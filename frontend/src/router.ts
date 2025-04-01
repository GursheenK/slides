import { createRouter, createWebHistory } from 'vue-router'

import { call } from 'frappe-ui'

import { session } from '@/stores/session'

const routes = [
	{
		path: '/',
		name: 'Home',
		component: () => import('@/pages/Home.vue'),
	},
	{
		path: '/presentation/:presentationId',
		name: 'PresentationEditor',
		component: () => import('@/pages/PresentationEditor.vue'),
	},
	{
		path: '/slideshow/:presentationId',
		name: 'Slideshow',
		component: () => import('@/pages/Slideshow.vue'),
	},
	{
		path: '/not-permitted',
		name: 'NotPermitted',
		component: () => import('@/pages/errorPages/NotPermitted.vue'),
	},
	{
		path: '/demo',
		name: 'Demo',
		component: () => import('@/demo/Demo.vue'),
	}
]

let router = createRouter({
	history: createWebHistory('/slides'),
	routes,
})

const hasAccess = async (presentationId: string) => {
	try {
		const response = await call('frappe.client.has_permission', {
			doctype: 'Presentation',
			docname: presentationId,
			perm_type: 'write',
		})
		return response.has_permission
	} catch (error) {
		console.error('Permission check failed:', error)
		return false
	}
}

router.beforeEach(async (to, _, next) => {
	const isLoggedIn = session.isLoggedIn

	if (!isLoggedIn) {
		if (to.path !== '/login') window.location.href = '/login?redirect-to=' + to.path
		next()
	} else {
		if (to.path === '/login') {
			next({ name: 'Home' })
		} else if (['PresentationEditor', 'Slideshow'].includes(to.name as string)) {
			const canAccess = await hasAccess(to.params.presentationId as string)

			if (canAccess) {
				next()
			} else {
				next({ name: 'NotPermitted' })
			}
		} else {
			next()
		}
	}
})

export default router
