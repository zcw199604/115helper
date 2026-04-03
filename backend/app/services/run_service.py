"""任务运行服务，串联同步扫描、上传与结果落库。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.integrations.p115.client import P115Gateway
from app.models.enums import DuplicateCheckMode, FileAction, RunStatus, TriggerType, UploadFlowMode, UploadMode
from app.models.file_record import FileRecord
from app.models.run import JobRun
from app.models.source import SyncSource
from app.schemas.run import FileRecordRead, RunDetail, RunRead
from app.services.async_run_executor import async_run_executor
from app.services.remote_dir_cache_service import RemoteDirCacheService
from app.services.scheduler_service import scheduler_service
from app.services.sync_scanner import scan_local_files
from app.services.task_log_service import TaskLogService
from app.services.upload_strategy import RemoteDirContext, UploadResult, UploadStrategyService


@dataclass
class StagedCandidateResult:
    candidate: object
    final_remote_dir_path: str
    final_remote_file_path: str
    stage_remote_dir_path: str
    stage_remote_file_path: str
    result: UploadResult


class RunService:
    """运行记录与执行入口。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.log_service = TaskLogService(db)
        self.remote_cache_service = RemoteDirCacheService(db)

    def ensure_run_exists(self, run_id: int) -> JobRun:
        run = self.db.get(JobRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail='运行记录不存在')
        return run

    def _get_source_or_404(self, source_id: int) -> SyncSource:
        source = self.db.get(SyncSource, source_id)
        if source is None:
            raise HTTPException(status_code=404, detail='同步任务不存在')
        return source

    def ensure_source_idle(self, source_id: int) -> None:
        if scheduler_service.is_reserved(source_id):
            raise HTTPException(status_code=409, detail='该同步任务已有运行中的任务')

    def create_run(self, source_id: int, trigger_type: TriggerType) -> JobRun:
        run = JobRun(source_id=source_id, trigger_type=trigger_type.value, status=RunStatus.PENDING.value, summary_json='{}')
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        self.log_service.log(run_id=run.id, source_id=source_id, level='INFO', stage='created', message=f'任务已创建，触发方式: {trigger_type.value}')
        self.log_service.publish_status(run_id=run.id, source_id=source_id, status=RunStatus.PENDING.value)
        return run

    def _cancel_requested(self, run_id: int) -> bool:
        return async_run_executor.is_cancel_requested(run_id)

    def _stop_if_cancelled(self, run: JobRun, source: SyncSource, stage: str, summary: dict | None = None) -> bool:
        if not self._cancel_requested(run.id):
            return False
        run.status = RunStatus.CANCELLED.value
        run.finished_at = datetime.now(timezone.utc)
        if summary is not None:
            run.summary_json = json.dumps(summary, ensure_ascii=False)
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        self.log_service.log(run_id=run.id, source_id=source.id, level='WARNING', stage=stage, message='检测到取消请求，任务执行已中断')
        self.log_service.publish_status(run_id=run.id, source_id=source.id, status=RunStatus.CANCELLED.value)
        scheduler_service.release_source(source.id)
        return True

    @staticmethod
    def _resolve_upload_flow_mode(source: SyncSource) -> UploadFlowMode:
        raw_value = getattr(source, 'upload_flow_mode', None) or UploadFlowMode.PLUGIN_ALIGNED.value
        return UploadFlowMode(raw_value)

    def _log(self, *, run: JobRun, source: SyncSource, level: str, stage: str, message: str) -> None:
        self.log_service.log(run_id=run.id, source_id=source.id, level=level, stage=stage, message=message)

    def _append_summary(self, *, summary: dict, action: FileAction) -> None:
        if action == FileAction.FAST_UPLOADED:
            summary['fast_uploaded'] += 1
        elif action == FileAction.MULTIPART_UPLOADED:
            summary['multipart_uploaded'] += 1
        elif action == FileAction.SKIPPED:
            summary['skipped'] += 1
        elif action == FileAction.FAILED:
            summary['failed'] += 1

    def _write_file_record(
        self,
        *,
        run: JobRun,
        source: SyncSource,
        candidate,
        action: FileAction,
        message: str,
        file_sha1: str | None,
        remote_file_id: str | None,
        remote_pickcode: str | None,
    ) -> None:
        self.db.add(
            FileRecord(
                run_id=run.id,
                source_id=source.id,
                relative_path=candidate.relative_path.as_posix(),
                file_size=candidate.size,
                file_sha1=file_sha1,
                suffix=candidate.suffix,
                action=action.value,
                remote_file_id=remote_file_id,
                remote_pickcode=remote_pickcode,
                message=message,
            )
        )
        self.db.commit()

    @staticmethod
    def _find_missing_root(gateway: P115Gateway, remote_dir_path: str) -> str | None:
        target = PurePosixPath(remote_dir_path)
        if gateway.get_dir_id_by_path(target) > 0:
            return None
        current = PurePosixPath('/')
        for part in target.parts[1:]:
            candidate = current.joinpath(part)
            if gateway.get_dir_id_by_path(candidate) > 0:
                current = candidate
                continue
            return candidate.as_posix()
        return target.as_posix()

    @staticmethod
    def _build_stage_remote_root(run: JobRun, source: SyncSource) -> str:
        return f"/tmp/115helper_stage/source_{source.id}/run_{run.id}"

    def _process_direct_candidate(
        self,
        *,
        run: JobRun,
        source: SyncSource,
        uploader: UploadStrategyService,
        gateway: P115Gateway,
        candidate,
        remote_dir_path: str,
        remote_file_path: str,
        duplicate_check_mode: DuplicateCheckMode,
        force_refresh_remote_cache: bool,
        summary: dict,
    ) -> None:
        if self._stop_if_cancelled(run, source, 'file', summary):
            return
        self._log(run=run, source=source, level='INFO', stage='file', message=f'开始处理文件: {candidate.relative_path.as_posix()} ({candidate.size} bytes)')
        try:
            context = uploader.prepare_plugin_aligned_context(
                remote_dir_path=remote_dir_path,
                duplicate_check_mode=duplicate_check_mode,
                force_refresh_remote_cache=force_refresh_remote_cache,
                log=lambda message, candidate=candidate: self._log(run=run, source=source, level='INFO', stage='remote-dir-prepare', message=f"{candidate.relative_path.as_posix()} -> {message}"),
                is_cancel_requested=lambda: self._cancel_requested(run.id),
            )
            result = uploader.upload_candidate_in_context(
                candidate,
                context,
                UploadMode(source.upload_mode),
                duplicate_check_mode=duplicate_check_mode,
                log=lambda message, candidate=candidate: self._log(run=run, source=source, level='INFO', stage='open-upload', message=f"{candidate.relative_path.as_posix()} -> {message}"),
                is_cancel_requested=lambda: self._cancel_requested(run.id),
            )
            if result.action in {FileAction.FAST_UPLOADED, FileAction.MULTIPART_UPLOADED}:
                verified = uploader.verify_uploaded_file(
                    remote_file_path=remote_file_path,
                    context=context,
                    file_sha1=result.file_sha1,
                    size=candidate.size,
                    log=lambda message, candidate=candidate: self._log(run=run, source=source, level='INFO', stage='remote-verify', message=f"{candidate.relative_path.as_posix()} -> {message}"),
                    is_cancel_requested=lambda: self._cancel_requested(run.id),
                )
                if verified is not None:
                    result.remote_file_id = str(verified.get('id') or '') or result.remote_file_id
                    result.remote_pickcode = verified.get('pickcode') or result.remote_pickcode
                    result.message = f'{result.message}；上传后轮询确认成功'
                else:
                    result.message = f'{result.message}；上传后轮询未确认'
            self._append_summary(summary=summary, action=result.action)
            self._write_file_record(
                run=run,
                source=source,
                candidate=candidate,
                action=result.action,
                message=result.message,
                file_sha1=result.file_sha1,
                remote_file_id=result.remote_file_id,
                remote_pickcode=result.remote_pickcode,
            )
            self._log(run=run, source=source, level='INFO', stage='upload', message=f'文件处理完成: {candidate.relative_path.as_posix()} -> {result.message}')
        except Exception as exc:
            message = gateway.humanize_error(exc)
            self._append_summary(summary=summary, action=FileAction.FAILED)
            self._write_file_record(
                run=run,
                source=source,
                candidate=candidate,
                action=FileAction.FAILED,
                message=message,
                file_sha1=None,
                remote_file_id=None,
                remote_pickcode=None,
            )
            self._log(run=run, source=source, level='ERROR', stage='upload', message=f'文件处理失败: {candidate.relative_path.as_posix()} -> {message}')

    def _execute_plugin_aligned_flow(
        self,
        *,
        run: JobRun,
        source: SyncSource,
        uploader: UploadStrategyService,
        gateway: P115Gateway,
        candidates: list,
        duplicate_check_mode: DuplicateCheckMode,
        force_refresh_remote_cache: bool,
        summary: dict,
    ) -> None:
        for candidate in candidates:
            remote_dir_path = uploader.resolve_remote_dir_path(source.remote_path, candidate)
            remote_file_path = uploader.resolve_remote_file_path(source.remote_path, candidate)
            self._process_direct_candidate(
                run=run,
                source=source,
                uploader=uploader,
                gateway=gateway,
                candidate=candidate,
                remote_dir_path=remote_dir_path,
                remote_file_path=remote_file_path,
                duplicate_check_mode=duplicate_check_mode,
                force_refresh_remote_cache=force_refresh_remote_cache,
                summary=summary,
            )

    def _execute_batch_cached_flow(
        self,
        *,
        run: JobRun,
        source: SyncSource,
        uploader: UploadStrategyService,
        gateway: P115Gateway,
        candidates: list,
        duplicate_check_mode: DuplicateCheckMode,
        force_refresh_remote_cache: bool,
        summary: dict,
    ) -> None:
        grouped_candidates: dict[str, list] = {}
        for candidate in candidates:
            remote_dir_path = uploader.resolve_remote_dir_path(source.remote_path, candidate)
            grouped_candidates.setdefault(remote_dir_path, []).append(candidate)

        if grouped_candidates:
            uploader.precreate_remote_dirs(
                list(grouped_candidates.keys()),
                log=lambda message: self._log(run=run, source=source, level='INFO', stage='remote-dir-prepare', message=message),
                is_cancel_requested=lambda: self._cancel_requested(run.id),
            )
            if self._stop_if_cancelled(run, source, 'remote-dir-prepare', summary):
                return

        for remote_dir_path, dir_candidates in grouped_candidates.items():
            context = uploader.prepare_dir_context(
                remote_dir_path=remote_dir_path,
                force_refresh_remote_cache=force_refresh_remote_cache,
                log=lambda message: self._log(run=run, source=source, level='INFO', stage='remote-cache', message=message),
                is_cancel_requested=lambda: self._cancel_requested(run.id),
            )
            for candidate in dir_candidates:
                if self._stop_if_cancelled(run, source, 'file', summary):
                    return
                remote_file_path = uploader.resolve_remote_file_path(source.remote_path, candidate)
                try:
                    result = uploader.upload_candidate_in_context(
                        candidate,
                        context,
                        UploadMode(source.upload_mode),
                        duplicate_check_mode=duplicate_check_mode,
                        log=lambda message, candidate=candidate: self._log(run=run, source=source, level='INFO', stage='open-upload', message=f"{candidate.relative_path.as_posix()} -> {message}"),
                        is_cancel_requested=lambda: self._cancel_requested(run.id),
                    )
                    if result.action in {FileAction.FAST_UPLOADED, FileAction.MULTIPART_UPLOADED}:
                        verified = uploader.verify_uploaded_file(
                            remote_file_path=remote_file_path,
                            context=context,
                            file_sha1=result.file_sha1,
                            size=candidate.size,
                            log=lambda message, candidate=candidate: self._log(run=run, source=source, level='INFO', stage='remote-verify', message=f"{candidate.relative_path.as_posix()} -> {message}"),
                            is_cancel_requested=lambda: self._cancel_requested(run.id),
                        )
                        if verified is not None:
                            result.remote_file_id = str(verified.get('id') or '') or result.remote_file_id
                            result.remote_pickcode = verified.get('pickcode') or result.remote_pickcode
                            result.message = f'{result.message}；上传后轮询确认成功'
                    self._append_summary(summary=summary, action=result.action)
                    self._write_file_record(run=run, source=source, candidate=candidate, action=result.action, message=result.message, file_sha1=result.file_sha1, remote_file_id=result.remote_file_id, remote_pickcode=result.remote_pickcode)
                except Exception as exc:
                    message = gateway.humanize_error(exc)
                    self._append_summary(summary=summary, action=FileAction.FAILED)
                    self._write_file_record(run=run, source=source, candidate=candidate, action=FileAction.FAILED, message=message, file_sha1=None, remote_file_id=None, remote_pickcode=None)

    def _execute_tmp_stage_then_move_flow(
        self,
        *,
        run: JobRun,
        source: SyncSource,
        uploader: UploadStrategyService,
        gateway: P115Gateway,
        candidates: list,
        duplicate_check_mode: DuplicateCheckMode,
        force_refresh_remote_cache: bool,
        summary: dict,
    ) -> None:
        stage_root = self._build_stage_remote_root(run, source)
        staged_jobs: dict[str, dict] = {}
        direct_candidates: list = []
        for candidate in candidates:
            final_remote_dir_path = uploader.resolve_remote_dir_path(source.remote_path, candidate)
            missing_root = self._find_missing_root(gateway, final_remote_dir_path)
            if missing_root is None:
                direct_candidates.append(candidate)
                continue
            staged_jobs.setdefault(missing_root, {'candidates': [], 'final_parent': str(PurePosixPath(missing_root).parent)})['candidates'].append(candidate)

        for candidate in direct_candidates:
            remote_dir_path = uploader.resolve_remote_dir_path(source.remote_path, candidate)
            remote_file_path = uploader.resolve_remote_file_path(source.remote_path, candidate)
            self._process_direct_candidate(
                run=run,
                source=source,
                uploader=uploader,
                gateway=gateway,
                candidate=candidate,
                remote_dir_path=remote_dir_path,
                remote_file_path=remote_file_path,
                duplicate_check_mode=duplicate_check_mode,
                force_refresh_remote_cache=force_refresh_remote_cache,
                summary=summary,
            )

        for missing_root, job in staged_jobs.items():
            if self._stop_if_cancelled(run, source, 'tmp-stage', summary):
                return
            self._log(run=run, source=source, level='INFO', stage='tmp-stage', message=f'目标目录不存在，启用临时目录上传: {missing_root}')
            staged_results: list[StagedCandidateResult] = []
            stage_failed = False
            for candidate in job['candidates']:
                final_remote_dir_path = uploader.resolve_remote_dir_path(source.remote_path, candidate)
                final_remote_file_path = uploader.resolve_remote_file_path(source.remote_path, candidate)
                stage_remote_dir_path = PurePosixPath(stage_root).joinpath(*PurePosixPath(final_remote_dir_path).parts[1:]).as_posix()
                stage_remote_file_path = PurePosixPath(stage_root).joinpath(*PurePosixPath(final_remote_file_path).parts[1:]).as_posix()
                try:
                    context = uploader.prepare_plugin_aligned_context(
                        remote_dir_path=stage_remote_dir_path,
                        duplicate_check_mode=DuplicateCheckMode.NONE,
                        force_refresh_remote_cache=force_refresh_remote_cache,
                        log=lambda message, candidate=candidate: self._log(run=run, source=source, level='INFO', stage='tmp-stage', message=f"{candidate.relative_path.as_posix()} -> {message}"),
                        is_cancel_requested=lambda: self._cancel_requested(run.id),
                    )
                    result = uploader.upload_candidate_in_context(
                        candidate,
                        context,
                        UploadMode(source.upload_mode),
                        duplicate_check_mode=DuplicateCheckMode.NONE,
                        log=lambda message, candidate=candidate: self._log(run=run, source=source, level='INFO', stage='open-upload', message=f"{candidate.relative_path.as_posix()} -> {message}"),
                        is_cancel_requested=lambda: self._cancel_requested(run.id),
                    )
                    if result.action not in {FileAction.FAST_UPLOADED, FileAction.MULTIPART_UPLOADED}:
                        staged_results.append(StagedCandidateResult(candidate, final_remote_dir_path, final_remote_file_path, stage_remote_dir_path, stage_remote_file_path, result))
                        stage_failed = True
                        continue
                    verified = uploader.verify_uploaded_file(
                        remote_file_path=stage_remote_file_path,
                        context=context,
                        file_sha1=result.file_sha1,
                        size=candidate.size,
                        log=lambda message, candidate=candidate: self._log(run=run, source=source, level='INFO', stage='remote-verify', message=f"{candidate.relative_path.as_posix()} -> {message}"),
                        is_cancel_requested=lambda: self._cancel_requested(run.id),
                    )
                    if verified is not None:
                        result.remote_file_id = str(verified.get('id') or '') or result.remote_file_id
                        result.remote_pickcode = verified.get('pickcode') or result.remote_pickcode
                    result.message = f'{result.message}；已上传到临时目录'
                    staged_results.append(StagedCandidateResult(candidate, final_remote_dir_path, final_remote_file_path, stage_remote_dir_path, stage_remote_file_path, result))
                except Exception as exc:
                    result = UploadResult(action=FileAction.FAILED, message=gateway.humanize_error(exc))
                    staged_results.append(StagedCandidateResult(candidate, final_remote_dir_path, final_remote_file_path, stage_remote_dir_path, stage_remote_file_path, result))
                    stage_failed = True

            if stage_failed:
                for item in staged_results:
                    self._append_summary(summary=summary, action=item.result.action if item.result.action != FileAction.FAST_UPLOADED and item.result.action != FileAction.MULTIPART_UPLOADED else FileAction.FAILED)
                    action = item.result.action if item.result.action in {FileAction.SKIPPED, FileAction.FAILED} else FileAction.FAILED
                    message = item.result.message if action in {FileAction.SKIPPED, FileAction.FAILED} else f'{item.result.message}；临时目录阶段未全部完成，未执行移动'
                    self._write_file_record(run=run, source=source, candidate=item.candidate, action=action, message=message, file_sha1=item.result.file_sha1, remote_file_id=item.result.remote_file_id, remote_pickcode=item.result.remote_pickcode)
                continue

            try:
                stage_missing_root = PurePosixPath(stage_root).joinpath(*PurePosixPath(missing_root).parts[1:])
                final_parent = PurePosixPath(job['final_parent'])
                self._log(run=run, source=source, level='INFO', stage='tmp-move', message=f'开始移动临时目录到最终位置: {stage_missing_root.as_posix()} -> {final_parent.as_posix()}')
                gateway.move_dir(source_dir_path=stage_missing_root, target_parent_path=final_parent)
                self._log(run=run, source=source, level='INFO', stage='tmp-move', message=f'临时目录移动完成: {missing_root}')
                for item in staged_results:
                    final_dir_id = gateway.get_dir_id_by_path(PurePosixPath(item.final_remote_dir_path))
                    final_context = RemoteDirContext(remote_dir_id=final_dir_id, remote_dir_path=item.final_remote_dir_path, items=[])
                    verified = uploader.verify_uploaded_file(
                        remote_file_path=item.final_remote_file_path,
                        context=final_context,
                        file_sha1=item.result.file_sha1,
                        size=item.candidate.size,
                        log=lambda message, candidate=item.candidate: self._log(run=run, source=source, level='INFO', stage='remote-verify', message=f"{candidate.relative_path.as_posix()} -> {message}"),
                        is_cancel_requested=lambda: self._cancel_requested(run.id),
                    )
                    if verified is not None:
                        item.result.remote_file_id = str(verified.get('id') or '') or item.result.remote_file_id
                        item.result.remote_pickcode = verified.get('pickcode') or item.result.remote_pickcode
                        item.result.message = f'{item.result.message}；临时目录已移动到最终目录并确认成功'
                    else:
                        item.result.message = f'{item.result.message}；临时目录已移动到最终目录，但最终路径确认未命中'
                    self._append_summary(summary=summary, action=item.result.action)
                    self._write_file_record(run=run, source=source, candidate=item.candidate, action=item.result.action, message=item.result.message, file_sha1=item.result.file_sha1, remote_file_id=item.result.remote_file_id, remote_pickcode=item.result.remote_pickcode)
            except Exception as exc:
                message = gateway.humanize_error(exc)
                self._log(run=run, source=source, level='ERROR', stage='tmp-move', message=f'临时目录移动失败: {missing_root} -> {message}')
                for item in staged_results:
                    self._append_summary(summary=summary, action=FileAction.FAILED)
                    self._write_file_record(run=run, source=source, candidate=item.candidate, action=FileAction.FAILED, message=f'{item.result.message}；临时目录移动失败: {message}', file_sha1=item.result.file_sha1, remote_file_id=item.result.remote_file_id, remote_pickcode=item.result.remote_pickcode)

    def execute_run(self, run_id: int) -> JobRun:
        run = self.ensure_run_exists(run_id)
        source = self._get_source_or_404(run.source_id)
        if run.status == RunStatus.CANCELLED.value or self._cancel_requested(run.id):
            self.log_service.publish_status(run_id=run.id, source_id=source.id, status=RunStatus.CANCELLED.value)
            scheduler_service.release_source(source.id)
            return run
        reserved_here = False
        if not scheduler_service.is_reserved(source.id):
            if not scheduler_service.reserve_source(source.id):
                raise HTTPException(status_code=409, detail='该同步任务已有运行中的任务')
            reserved_here = True
        gateway = P115Gateway()
        summary = {'total_files': 0, 'fast_uploaded': 0, 'multipart_uploaded': 0, 'skipped': 0, 'failed': 0}
        try:
            run.status = RunStatus.RUNNING.value
            run.started_at = datetime.now(timezone.utc)
            self.db.add(run)
            self.db.commit()
            self.log_service.log(run_id=run.id, source_id=source.id, level='INFO', stage='started', message=f'任务开始执行: {source.name}')
            self.log_service.publish_status(run_id=run.id, source_id=source.id, status=RunStatus.RUNNING.value)
            if self._stop_if_cancelled(run, source, 'started', summary):
                return run

            suffix_rules = json.loads(source.suffix_rules_json or '[]')
            exclude_rules = json.loads(source.exclude_rules_json or '[]')
            candidates = scan_local_files(Path(source.local_path), suffix_rules, exclude_rules)
            summary['total_files'] = len(candidates)
            duplicate_check_mode = DuplicateCheckMode(getattr(source, 'duplicate_check_mode', None) or ('sha1' if bool(getattr(source, 'skip_existing_remote', 0)) else 'none'))
            mode_text = {'none': '关闭', 'name': '按文件名', 'sha1': '按 SHA1'}[duplicate_check_mode.value]
            force_refresh_remote_cache = bool(getattr(source, 'force_refresh_remote_cache', 0))
            refresh_text = '强制同步远端目录文件' if force_refresh_remote_cache else '按需使用本地远端目录缓存'
            upload_flow_mode = self._resolve_upload_flow_mode(source)
            flow_text = {
                UploadFlowMode.PLUGIN_ALIGNED: '插件对齐',
                UploadFlowMode.BATCH_CACHED: '批处理缓存',
                UploadFlowMode.TMP_STAGE_THEN_MOVE: '临时目录上传后移动',
            }[upload_flow_mode]
            self.log_service.log(run_id=run.id, source_id=source.id, level='INFO', stage='scan', message=f"扫描完成，候选文件 {len(candidates)} 个；后缀规则 {suffix_rules or ['全部']}；排除规则 {exclude_rules or ['无']}；远端防重 {mode_text}；目录缓存策略 {refresh_text}；执行方式 {flow_text}")
            if self._stop_if_cancelled(run, source, 'scan', summary):
                return run

            uploader = UploadStrategyService(gateway, self.remote_cache_service)
            if upload_flow_mode == UploadFlowMode.BATCH_CACHED:
                self._execute_batch_cached_flow(run=run, source=source, uploader=uploader, gateway=gateway, candidates=candidates, duplicate_check_mode=duplicate_check_mode, force_refresh_remote_cache=force_refresh_remote_cache, summary=summary)
            elif upload_flow_mode == UploadFlowMode.TMP_STAGE_THEN_MOVE:
                self._execute_tmp_stage_then_move_flow(run=run, source=source, uploader=uploader, gateway=gateway, candidates=candidates, duplicate_check_mode=duplicate_check_mode, force_refresh_remote_cache=force_refresh_remote_cache, summary=summary)
            else:
                self._execute_plugin_aligned_flow(run=run, source=source, uploader=uploader, gateway=gateway, candidates=candidates, duplicate_check_mode=duplicate_check_mode, force_refresh_remote_cache=force_refresh_remote_cache, summary=summary)

            run.summary_json = json.dumps(summary, ensure_ascii=False)
            run.finished_at = datetime.now(timezone.utc)
            if summary['failed']:
                run.status = RunStatus.PARTIAL_FAILED.value if summary['fast_uploaded'] or summary['multipart_uploaded'] else RunStatus.FAILED.value
            else:
                run.status = RunStatus.SUCCESS.value
            self.db.add(run)
            self.db.commit()
            self.db.refresh(run)
            self.log_service.log(run_id=run.id, source_id=source.id, level='INFO', stage='finished', message=f'任务执行结束，状态: {run.status}，统计: {summary}')
            self.log_service.publish_status(run_id=run.id, source_id=source.id, status=run.status)
            return run
        finally:
            if reserved_here or scheduler_service.is_reserved(source.id):
                scheduler_service.release_source(source.id)

    def list_runs(self, source_id: int | None = None) -> list[RunRead]:
        query = self.db.query(JobRun)
        if source_id is not None:
            query = query.filter(JobRun.source_id == source_id)
        runs = query.order_by(JobRun.id.desc()).all()
        return [self._to_read_model(run) for run in runs]

    def get_run_detail(self, run_id: int) -> RunDetail:
        run = self.ensure_run_exists(run_id)
        records = [FileRecordRead.model_validate(record) for record in self.db.query(FileRecord).filter(FileRecord.run_id == run_id).order_by(FileRecord.id.asc()).all()]
        logs = self.log_service.list_by_run(run_id)
        return RunDetail(**self._to_read_model(run).model_dump(), records=records, logs=logs)

    def list_logs(self, run_id: int):
        self.ensure_run_exists(run_id)
        return self.log_service.list_by_run(run_id)

    def retry_run_async(self, run_id: int) -> RunRead:
        run = self.ensure_run_exists(run_id)
        self.ensure_source_idle(run.source_id)
        if not scheduler_service.reserve_source(run.source_id):
            raise HTTPException(status_code=409, detail='该同步任务已有运行中的任务')
        retry = self.create_run(run.source_id, TriggerType.RETRY)
        return self._to_read_model(retry)

    def cancel_run(self, run_id: int) -> RunRead:
        run = self.ensure_run_exists(run_id)
        source = self._get_source_or_404(run.source_id)
        if run.status in {RunStatus.SUCCESS.value, RunStatus.FAILED.value, RunStatus.PARTIAL_FAILED.value, RunStatus.CANCELLED.value}:
            return self._to_read_model(run)
        async_run_executor.request_cancel(run.id)
        self.log_service.log(run_id=run.id, source_id=run.source_id, level='WARNING', stage='cancel-request', message='已收到取消请求，任务将在检查点中断')
        if run.status == RunStatus.PENDING.value:
            run.status = RunStatus.CANCELLED.value
            run.finished_at = datetime.now(timezone.utc)
            self.db.add(run)
            self.db.commit()
            self.db.refresh(run)
            self.log_service.log(run_id=run.id, source_id=run.source_id, level='WARNING', stage='cancelled', message='任务在启动前已取消')
            self.log_service.publish_status(run_id=run.id, source_id=run.source_id, status=RunStatus.CANCELLED.value)
            scheduler_service.release_source(source.id)
            async_run_executor.clear_run(run.id)
        return self._to_read_model(run)

    def _to_read_model(self, run: JobRun) -> RunRead:
        source = self._get_source_or_404(run.source_id)
        return RunRead(id=run.id, source_id=run.source_id, source_name=source.name, trigger_type=TriggerType(run.trigger_type), status=RunStatus(run.status), started_at=run.started_at, finished_at=run.finished_at, summary=json.loads(run.summary_json or '{}'), error_message=run.error_message, created_at=run.created_at)
