"""任务运行服务，串联同步扫描、上传与结果落库。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.integrations.p115.client import P115Gateway
from app.models.enums import DuplicateCheckMode, FileAction, RunStatus, TriggerType, UploadMode
from app.models.file_record import FileRecord
from app.models.run import JobRun
from app.models.source import SyncSource
from app.schemas.run import FileRecordRead, RunDetail, RunRead
from app.services.async_run_executor import async_run_executor
from app.services.remote_dir_cache_service import RemoteDirCacheService
from app.services.scheduler_service import scheduler_service
from app.services.sync_scanner import scan_local_files
from app.services.task_log_service import TaskLogService
from app.services.upload_strategy import UploadStrategyService


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
            refresh_text = '强制同步远端目录文件' if force_refresh_remote_cache else '优先使用本地远端目录缓存'
            self.log_service.log(run_id=run.id, source_id=source.id, level='INFO', stage='scan', message=f"扫描完成，候选文件 {len(candidates)} 个；后缀规则 {suffix_rules or ['全部']}；排除规则 {exclude_rules or ['无']}；远端防重 {mode_text}；目录缓存策略 {refresh_text}")
            if self._stop_if_cancelled(run, source, 'scan', summary):
                return run

            uploader = UploadStrategyService(gateway, self.remote_cache_service)
            grouped_candidates: dict[str, list] = {}
            for candidate in candidates:
                remote_dir_path = uploader.resolve_remote_dir_path(source.remote_path, candidate)
                grouped_candidates.setdefault(remote_dir_path, []).append(candidate)

            for remote_dir_path, dir_candidates in grouped_candidates.items():
                if self._stop_if_cancelled(run, source, 'dir', summary):
                    return run
                self.log_service.log(run_id=run.id, source_id=source.id, level='INFO', stage='remote-dir', message=f'开始处理远端目录批次: {remote_dir_path}，文件数 {len(dir_candidates)}')
                context = uploader.prepare_dir_context(
                    remote_dir_path=remote_dir_path,
                    force_refresh_remote_cache=force_refresh_remote_cache,
                    log=lambda message: self.log_service.log(run_id=run.id, source_id=source.id, level='INFO', stage='remote-cache', message=message),
                )
                for candidate in dir_candidates:
                    if self._stop_if_cancelled(run, source, 'file', summary):
                        return run
                    self.log_service.log(run_id=run.id, source_id=source.id, level='INFO', stage='file', message=f'开始处理文件: {candidate.relative_path.as_posix()} ({candidate.size} bytes)')
                    try:
                        result = uploader.upload_candidate_in_context(
                            candidate,
                            context,
                            UploadMode(source.upload_mode),
                            duplicate_check_mode=duplicate_check_mode,
                        )
                        if result.action == FileAction.FAST_UPLOADED:
                            summary['fast_uploaded'] += 1
                        elif result.action == FileAction.MULTIPART_UPLOADED:
                            summary['multipart_uploaded'] += 1
                        elif result.action == FileAction.SKIPPED:
                            summary['skipped'] += 1
                        action = result.action.value
                        message = result.message
                        file_sha1 = result.file_sha1
                        remote_file_id = result.remote_file_id
                        remote_pickcode = result.remote_pickcode
                        self.log_service.log(run_id=run.id, source_id=source.id, level='INFO', stage='upload', message=f'文件处理完成: {candidate.relative_path.as_posix()} -> {message}')
                    except Exception as exc:
                        summary['failed'] += 1
                        action = FileAction.FAILED.value
                        message = gateway.humanize_error(exc)
                        file_sha1 = None
                        remote_file_id = None
                        remote_pickcode = None
                        self.log_service.log(run_id=run.id, source_id=source.id, level='ERROR', stage='upload', message=f'文件处理失败: {candidate.relative_path.as_posix()} -> {message}')

                    self.db.add(FileRecord(run_id=run.id, source_id=source.id, relative_path=candidate.relative_path.as_posix(), file_size=candidate.size, file_sha1=file_sha1, suffix=candidate.suffix, action=action, remote_file_id=remote_file_id, remote_pickcode=remote_pickcode, message=message))
                    self.db.commit()
                    if self._stop_if_cancelled(run, source, 'upload', summary):
                        return run

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
