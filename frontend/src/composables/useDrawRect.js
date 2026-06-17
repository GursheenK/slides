import { ref, reactive } from 'vue'
import { slideBounds } from '@/stores/slide'

// Shared rect-drawing logic used by MarqueeOverlay and ShapeDrawOverlay
export function useDrawRect() {
	const isDrawing = ref(false)
	const drawRect = reactive({ left: 0, top: 0, width: 0, height: 0 })
	const startPoint = reactive({ x: 0, y: 0 })
	const endPoint = reactive({ x: 0, y: 0 })

	let startX = 0
	let startY = 0
	let endCallback = null

	const toSlideCoords = (e) => ({
		x: (e.clientX - slideBounds.left) / slideBounds.scale,
		y: (e.clientY - slideBounds.top) / slideBounds.scale,
	})

	const updateRect = (e) => {
		const { x, y } = toSlideCoords(e)
		endPoint.x = x
		endPoint.y = y
		drawRect.left = Math.min(x, startX)
		drawRect.top = Math.min(y, startY)
		drawRect.width = Math.abs(x - startX)
		drawRect.height = Math.abs(y - startY)
	}

	const endDrawing = () => {
		isDrawing.value = false
		document.removeEventListener('mousemove', updateRect)
		document.removeEventListener('mouseup', endDrawing)
		const rect = { ...drawRect }
		const p1 = { ...startPoint }
		const p2 = { ...endPoint }
		Object.assign(drawRect, { left: 0, top: 0, width: 0, height: 0 })
		endCallback?.(rect, p1, p2)
		endCallback = null
	}

	const startDrawing = (anchorEvent, onEnd) => {
		const { x, y } = toSlideCoords(anchorEvent)
		startX = x
		startY = y
		Object.assign(startPoint, { x, y })
		Object.assign(endPoint, { x, y })
		endCallback = onEnd
		isDrawing.value = true
		Object.assign(drawRect, { left: x, top: y, width: 0, height: 0 })

		document.addEventListener('mousemove', updateRect)
		document.addEventListener('mouseup', endDrawing)
	}

	// cancel without firing onEnd
	const cancel = () => {
		endCallback = null
		endDrawing()
	}

	return { isDrawing, drawRect, startPoint, endPoint, toSlideCoords, startDrawing, cancel }
}
