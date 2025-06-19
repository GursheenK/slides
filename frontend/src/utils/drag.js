import { ref } from 'vue'

export const useDragAndDrop = (snapOffsetX, snapOffsetY) => {
	const isDragging = ref(false)

	const prevX = ref(0)
	const prevY = ref(0)

	const positionDelta = ref({ x: 0, y: 0 })

	const startDragging = (e) => {
		e.preventDefault()
		e.stopPropagation()

		isDragging.value = true

		prevX.value = e.clientX
		prevY.value = e.clientY

		window.addEventListener('mousemove', drag)
		window.addEventListener('mouseup', stopDragging)
	}

	const drag = (e) => {
		e.preventDefault()

		const currentX = e.clientX - snapOffsetX.value
		const currentY = e.clientY - snapOffsetY.value

		if (isDragging.value) {
			const dx = currentX - prevX.value
			const dy = currentY - prevY.value

			positionDelta.value = {
				x: dx,
				y: dy,
			}

			prevX.value = currentX
			prevY.value = currentY
		}
	}

	const stopDragging = (e) => {
		e.preventDefault()
		e.stopPropagation()

		isDragging.value = false

		window.removeEventListener('mousemove', drag)
		window.removeEventListener('mouseup', stopDragging)
	}

	return { isDragging, positionDelta, startDragging }
}
