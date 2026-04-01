import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/sources',
    },
    {
      path: '/sources',
      name: 'sources',
      component: () => import('@/views/sources/SourceListView.vue'),
    },
    {
      path: '/sources/new',
      name: 'source-create',
      component: () => import('@/views/sources/SourceFormView.vue'),
    },
    {
      path: '/sources/:id/edit',
      name: 'source-edit',
      component: () => import('@/views/sources/SourceFormView.vue'),
      props: true,
    },
    {
      path: '/runs',
      name: 'runs',
      component: () => import('@/views/runs/RunListView.vue'),
    },
    {
      path: '/runs/:id',
      name: 'run-detail',
      component: () => import('@/views/runs/RunDetailView.vue'),
      props: true,
    },
  ],
})

export default router
