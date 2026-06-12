import { ref, computed, nextTick } from 'vue'

export const useResizer = () => {
	const isResizing = ref(false)
	const currentResizer = ref(null)

	const cursorMap = {
		'top-left': 'nwse-resize',
		'top-right': 'nesw-resize',
		'bottom-left': 'nesw-resize',
		'bottom-right': 'nwse-resize',
		'text-left': 'ew-resize',
		'text-right': 'ew-resize',
		left: 'ew-resize',
		right: 'ew-resize',
		top: 'ns-resize',
		bottom: 'ns-resize',
	}

	const resizeCursor = computed(() => cursorMap[currentResizer.value] ?? 'default')

	// last processed and latest cursor positions; diffs are summed
	// per animation frame instead of per mousemove
	let prevX = 0
	let prevY = 0
	let lastX = 0
	let lastY = 0
	let frame = null

	const dimensionDelta = ref({
		width: 0,
		height: 0,
		left: 0,
		top: 0,
	})

	const startResize = (e, resizer) => {
		e.preventDefault()
		e.stopImmediatePropagation()

		currentResizer.value = resizer
		isResizing.value = true

		prevX = lastX = e.clientX
		prevY = lastY = e.clientY

		window.addEventListener('mousemove', resize)
		window.addEventListener('mouseup', stopResize, { once: true })
	}

	const getDimensionDelta = (diffX, diffY, diffLeft, diffTop) => {
		let width = 0,
			height = 0,
			left = 0,
			top = 0
		if (['top', 'bottom'].includes(currentResizer.value)) {
			height = diffY
			top = diffTop
		} else {
			width = diffX
			height = diffY
			left = diffLeft
			top = diffTop
		}

		return {
			width: width,
			height: height,
			left: left,
			top: top,
		}
	}

	const flushResize = () => {
		frame = null

		let diffX = prevX - lastX
		let diffY = prevY - lastY

		let diffLeft = 0
		let diffTop = 0

		if (!diffX && !diffY) return

		switch (currentResizer.value) {
			case 'text-left':
				diffLeft = -diffX / 2
				diffY = 0
				break
			case 'text-right':
				diffLeft = -diffX / 2
				diffX = -diffX
				diffY = 0
				break
			case 'top-right':
				diffX = -diffX
				diffTop = -diffY
				break
			case 'bottom-left':
				diffLeft = -diffX
				diffY = -diffY
				break
			case 'top-left':
				diffLeft = -diffX
				diffTop = -diffY
				break
			case 'bottom-right':
				diffX = -diffX
				diffY = -diffY
				break
			case 'line-left':
			case 'left':
				diffLeft = -diffX
				diffY = 0
				break
			case 'bottom':
				diffY = -diffY
				diffX = 0
				break
			case 'top':
				diffTop = -diffY
				diffX = 0
				break
			case 'line-right':
			case 'right':
				diffX = -diffX
				diffY = 0
				break
			default:
				diffX = -diffX
				break
		}

		dimensionDelta.value = getDimensionDelta(diffX, diffY, diffLeft, diffTop)

		prevX = lastX
		prevY = lastY
	}

	const resize = (e) => {
		e.preventDefault()
		e.stopImmediatePropagation()

		lastX = e.clientX
		lastY = e.clientY

		if (!frame) frame = requestAnimationFrame(flushResize)
	}

	const stopResize = (e) => {
		e.preventDefault()
		e.stopImmediatePropagation()

		// flush movement still waiting on the next frame so the final size is exact
		if (frame) {
			cancelAnimationFrame(frame)
			flushResize()
		}

		isResizing.value = false

		// the flushed delta is processed by watchers after this task — they
		// still need the resizer context (aspect ratio, snap offsets), so
		// clear it only once the flush queue has drained
		nextTick(() => {
			currentResizer.value = null
		})

		window.removeEventListener('mousemove', resize)
		window.removeEventListener('mouseup', stopResize)
	}

	return { isResizing, dimensionDelta, currentResizer, startResize, resizeCursor }
}
