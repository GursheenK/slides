import { ref, reactive, computed } from 'vue'

export const useSnapping = (target, parent) => {
	const PROXIMITY_THRESHOLD = 30

	const snapMovement = ref({ x: 0, y: 0 })

	const recentSnap = ref(false)
	let snapTimeout = null

	const diffs = reactive({
		vertical: 0,
		horizontal: 0,
	})

	const prevDiffs = reactive({
		vertical: 0,
		horizontal: 0,
	})

	const possibleOffsets = reactive({
		vertical: 0,
		horizontal: 0,
	})

	const visibilityMap = computed(() => {
		if (!target.value) return { vertical: false, horizontal: false }
		return {
			vertical: Math.abs(diffs.vertical) < PROXIMITY_THRESHOLD,
			horizontal: Math.abs(diffs.horizontal) < PROXIMITY_THRESHOLD,
		}
	})

	const getElementBounds = (element) => {
		const rect = element.getBoundingClientRect()
		return {
			left: rect.left,
			top: rect.top,
			width: rect.width,
			height: rect.height,
		}
	}

	const getDiffFromCenter = (axis) => {
		if (!target.value) return
		let slideCenter, elementCenter

		const activeBounds = getElementBounds(target.value)
		const slideBounds = getElementBounds(parent.value)

		if (axis == 'X') {
			slideCenter = slideBounds.left + slideBounds.width / 2
			elementCenter = activeBounds.left + activeBounds.width / 2
		} else {
			slideCenter = slideBounds.top + slideBounds.height / 2
			elementCenter = activeBounds.top + activeBounds.height / 2
		}

		return elementCenter - slideCenter
	}

	const updateElementDiffs = () => {
		if (!target.value) return

		prevDiffs.vertical = diffs.vertical
		prevDiffs.horizontal = diffs.horizontal

		diffs.vertical = getDiffFromCenter('Y')
		diffs.horizontal = getDiffFromCenter('X')
	}

	const getSnapOffset = (diff, prevDiff) => {
		let offset = 0

		const canSnap =
			Math.abs(diff + PROXIMITY_THRESHOLD) < 3 || Math.abs(diff - PROXIMITY_THRESHOLD) < 3
		const movingAway = Math.abs(diff) > Math.abs(prevDiff)

		if (canSnap && !movingAway) {
			offset -= diff
		}

		return offset
	}

	const setPossibleSnapOffsets = () => {
		if (!target.value) return

		possibleOffsets.vertical = getSnapOffset(diffs.vertical, prevDiffs.vertical)
		possibleOffsets.horizontal = getSnapOffset(diffs.horizontal, prevDiffs.horizontal)
	}

	const handleSnap = (axis) => {
		let offset = 0

		if (possibleOffsets[axis]) {
			offset += possibleOffsets[axis]
			recentSnap.value = true

			clearTimeout(snapTimeout)
			snapTimeout = setTimeout(() => {
				recentSnap.value = false
			}, 400)
		}

		return offset
	}

	const updateSnapMovement = () => {
		if (!target.value) return

		snapMovement.value = {
			x: handleSnap('horizontal'),
			y: handleSnap('vertical'),
		}
	}

	const getSnapMovement = () => {
		if (!target.value) return

		setPossibleSnapOffsets()

		updateSnapMovement()

		return snapMovement.value
	}

	const getVisibilityMap = () => {
		updateElementDiffs()

		return visibilityMap.value
	}

	return { isMovementRestricted: recentSnap, getSnapMovement, getVisibilityMap }
}
