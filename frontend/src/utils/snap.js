import { ref, reactive, computed } from 'vue'
import { selectionBounds, slide, slideBounds } from '../stores/slide'
import { activeElementIds, pairElementId } from '../stores/element'

export const useSnapping = (target, parent) => {
	const CENTER_PROXIMITY_THRESHOLD = 12
	const PROXIMITY_THRESHOLD = 2

	const snapMovement = ref({ x: 0, y: 0 })

	const diffs = reactive({
		vertical: 0,
		horizontal: 0,
		left: 0,
		right: 0,
		top: 0,
		bottom: 0,
	})

	const prevDiffs = reactive({
		vertical: 0,
		horizontal: 0,
		left: 0,
		right: 0,
		top: 0,
		bottom: 0,
	})

	const visibilityMap = computed(() => {
		if (!target.value) return
		return {
			vertical: Math.abs(diffs.vertical) < CENTER_PROXIMITY_THRESHOLD,
			horizontal: Math.abs(diffs.horizontal) < CENTER_PROXIMITY_THRESHOLD,
			left: Math.abs(diffs.left) < PROXIMITY_THRESHOLD,
			right: Math.abs(diffs.right) < PROXIMITY_THRESHOLD,
			top: Math.abs(diffs.top) < PROXIMITY_THRESHOLD,
			bottom: Math.abs(diffs.bottom) < PROXIMITY_THRESHOLD,
		}
	})

	const getDiffFromCenter = (axis) => {
		if (!target.value) return
		let slideCenter, elementCenter

		if (axis == 'X') {
			const elementLeft = selectionBounds.left * slideBounds.scale + slideBounds.left
			const elementWidth = selectionBounds.width * slideBounds.scale

			slideCenter = slideBounds.left + slideBounds.width / 2
			elementCenter = elementLeft + elementWidth / 2
		} else {
			const elementTop = selectionBounds.top * slideBounds.scale + slideBounds.top
			const elementHeight = selectionBounds.height * slideBounds.scale

			slideCenter = slideBounds.top + slideBounds.height / 2
			elementCenter = elementTop + elementHeight / 2
		}

		return slideCenter - elementCenter
	}

	const canElementPair = (diffLeft, diffRight, diffTop, diffBottom) => {
		return (
			Math.abs(diffLeft) < PROXIMITY_THRESHOLD ||
			Math.abs(diffRight) < PROXIMITY_THRESHOLD ||
			Math.abs(diffTop) < PROXIMITY_THRESHOLD ||
			Math.abs(diffBottom) < PROXIMITY_THRESHOLD
		)
	}

	const getActiveElementBounds = () => {
		const scale = slideBounds.scale

		const bounds = Object.fromEntries(
			Object.entries(selectionBounds).map(([key, value]) => [key, value * scale]),
		)

		return {
			left: bounds.left + slideBounds.left,
			right: bounds.left + bounds.width + slideBounds.left,
			top: bounds.top + slideBounds.top,
			bottom: bounds.top + bounds.height + slideBounds.top,
		}
	}

	const setPairedDiffs = () => {
		slide.value.elements.forEach((element) => {
			if (activeElementIds.value.includes(element.id)) return

			const elementDiv = document.querySelector(`[data-index="${element.id}"]`)
			if (!elementDiv || !target.value) return

			const elementBounds = elementDiv.getBoundingClientRect()
			const activeBounds = getActiveElementBounds()

			const diffLeft = activeBounds.left - elementBounds.left
			const diffRight = activeBounds.right - elementBounds.right
			const diffTop = activeBounds.top - elementBounds.top
			const diffBottom = activeBounds.bottom - elementBounds.bottom

			const canPair = canElementPair(diffLeft, diffRight, diffTop, diffBottom)
			const isPaired = pairElementId.value == element.id

			if (canPair) {
				pairElementId.value = element.id

				diffs.left = diffLeft
				diffs.right = diffRight
				diffs.top = diffTop
				diffs.bottom = diffBottom
			} else if (isPaired) {
				pairElementId.value = null

				diffs.left = null
				diffs.right = null
				diffs.top = null
				diffs.bottom = null
			}
		})
	}

	const updateGuides = () => {
		if (!target.value) return

		prevDiffs.vertical = diffs.vertical
		prevDiffs.horizontal = diffs.horizontal
		prevDiffs.left = diffs.left
		prevDiffs.right = diffs.right
		prevDiffs.top = diffs.top
		prevDiffs.bottom = diffs.bottom

		diffs.vertical = getDiffFromCenter('Y')
		diffs.horizontal = getDiffFromCenter('X')

		setPairedDiffs()
	}

	const movingAwayX = ref(false)
	const movingAwayY = ref(false)

	const getSnapOffset = (axis) => {
		const diff = diffs[axis]
		const prevDiff = prevDiffs[axis]

		let threshold, margin
		if (['horizontal', 'vertical'].includes(axis)) {
			threshold = CENTER_PROXIMITY_THRESHOLD
			margin = 2
		} else {
			threshold = PROXIMITY_THRESHOLD
			margin = 3
		}

		let offset = 0

		const canSnap = Math.abs(diff + threshold) < margin || Math.abs(diff - threshold) < margin
		const movingAway = Math.abs(diff) > Math.abs(prevDiff)

		if (canSnap && !movingAway) {
			offset = diff
		}

		if (movingAway && Math.abs(diff) < threshold) {
			if (axis === 'horizontal' || axis === 'left' || axis === 'right') {
				movingAwayX.value = true
			} else if (axis === 'vertical' || axis === 'top' || axis === 'bottom') {
				movingAwayY.value = true
			}
		}

		if (movingAway && Math.abs(diff) > threshold) {
			if (axis === 'horizontal' || axis === 'left' || axis === 'right') {
				movingAwayX.value = false
			} else if (axis === 'vertical' || axis === 'top' || axis === 'bottom') {
				movingAwayY.value = false
			}
		}

		return offset
	}

	const applySnapMovement = (axis) => {
		let offset = 0

		const possibleOffset = getSnapOffset(axis)

		if (possibleOffset) {
			offset += possibleOffset
		}

		return offset
	}

	const getCenterOffsets = () => {
		return {
			offsetX: applySnapMovement('horizontal'),
			offsetY: applySnapMovement('vertical'),
		}
	}

	const getPairedOffsets = () => {
		let offsetLeft = 0,
			offsetTop = 0

		if (Math.abs(diffs.right) < Math.abs(diffs.left)) {
			offsetLeft = applySnapMovement('right')
		} else {
			offsetLeft = applySnapMovement('left')
		}

		if (Math.abs(diffs.bottom) < Math.abs(diffs.top)) {
			offsetTop = applySnapMovement('bottom')
		} else {
			offsetTop = applySnapMovement('top')
		}

		return { offsetLeft, offsetTop }
	}

	const getSnapDelta = () => {
		if (!target.value) return

		const { offsetX, offsetY } = getCenterOffsets()

		const { offsetLeft, offsetTop } = getPairedOffsets()

		return {
			x: offsetX - offsetLeft,
			y: offsetY - offsetTop,
		}
	}

	return {
		visibilityMap,
		movingAwayX,
		movingAwayY,
		updateGuides,
		getSnapDelta,
	}
}
