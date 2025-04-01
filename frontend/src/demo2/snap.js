import { reactive, ref, computed } from 'vue'

export const useSnap = (target, parent) => {
	const PROXIMITY_THRESHOLD = 15

	// let snapTimer

	// const recentSnap = ref(false)
	// const snapMovement = ref({ x: 0, y: 0 })

	const diffs = reactive({
		vertical: 0,
		horizontal: 0,
	})

	// const prevDiffs = reactive({
	//     vertical: 0,
	//     horizontal: 0
	// })

	// const possibleOffsets = reactive({
	//     vertical: 0,
	//     horizontal: 0
	// })

	// const visibilityMap = computed(() => {
	//     return { vertical: false, horizontal: false }
	// })

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
		const elementBounds = getElementBounds(target.value)
		const slideBounds = getElementBounds(parent.value)

		let slideCenter, elementCenter

		if (axis == 'Y') {
			slideCenter = slideBounds.left + slideBounds.width / 2
			elementCenter = elementBounds.left + elementBounds.width / 2
		} else {
			slideCenter = slideBounds.top + slideBounds.height / 2
			elementCenter = elementBounds.top + elementBounds.height / 2
		}

		return slideCenter - elementCenter
	}

	const calculateCenterDiffs = () => {
		diffs.vertical = getDiffFromCenter('X')
		diffs.horizontal = getDiffFromCenter('Y')
	}

	return { calculateCenterDiffs, visibilityMap }
}
