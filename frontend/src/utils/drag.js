import { watch, ref } from 'vue'

export const useDragAndDrop = (dragOffsets) => {
	const isDragging = ref(false)
	const mouseX = ref(0)
	const mouseY = ref(0)
	const movement = ref({ x: 0, y: 0 })

	let recentSnap = false

	let snapTimer = {
		x: 0,
		y: 0,
	}

	const startDragging = (e) => {
		e.preventDefault()
		e.stopPropagation()
		isDragging.value = true
		mouseX.value = e.clientX
		mouseY.value = e.clientY
		window.addEventListener('mousemove', drag)
		window.addEventListener('mouseup', stopDragging)
	}

	const makeSnapMovement = () => {
		let offsetX = 0
		let offsetY = 0

		if (!recentSnap) {
			if (dragOffsets.x) {
				console.log('here')
				offsetX += dragOffsets.x
				recentSnap = true
				clearTimeout(snapTimer.x)
				snapTimer.x = setTimeout(() => {
					recentSnap = false
				}, 300)
			}
		}

		if (!recentSnap) {
			if (dragOffsets.y) {
				offsetY += dragOffsets.y
				recentSnap = true
				clearTimeout(snapTimer.y)
				snapTimer.y = setTimeout(() => {
					recentSnap = false
				}, 300)
			}
		}

		return {
			offsetX,
			offsetY,
		}
	}

	const drag = (e) => {
		e.preventDefault()
		if (isDragging.value) {
			const dx = mouseX.value - e.clientX
			const dy = mouseY.value - e.clientY

			if (!recentSnap) {
				requestAnimationFrame(() => {
					movement.value = {
						x: -dx,
						y: -dy,
					}
				})
			}

			if (dragOffsets.x || dragOffsets.y) {
				const { offsetX, offsetY } = makeSnapMovement()
				console.log('snapping')
				requestAnimationFrame(() => {
					movement.value = {
						x: offsetX,
						y: offsetY,
					}
				})
			}

			mouseX.value = e.clientX
			mouseY.value = e.clientY
		}
	}

	const stopDragging = (e) => {
		e.preventDefault()
		e.stopPropagation()
		isDragging.value = false
		window.removeEventListener('mousemove', drag)
		window.removeEventListener('mouseup', stopDragging)
	}

	return { isDragging, movement, startDragging, recentSnap }
}
