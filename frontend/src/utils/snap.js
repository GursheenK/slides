import { ref, reactive } from 'vue'

export const useSnap = (snappableOffsets) => {
	const snapMovement = ref({ offsetX: 0, offsetY: 0 })

	const recentSnap = ref(false)
	let snapTimer = 0

	function handleSnap(axis) {
		let offset = 0

		if (!recentSnap.value && snappableOffsets[axis]) {
			offset += snappableOffsets[axis]
			recentSnap.value = true

			clearTimeout(snapTimer)
			snapTimer = setTimeout(() => {
				recentSnap.value = false
			}, 300)
		}

		return offset
	}

	const getSnapOffsets = () => {
		const offsetX = handleSnap('x')
		const offsetY = handleSnap('y')

		return {
			offsetX,
			offsetY,
		}
	}

	return { recentSnap, getSnapOffsets }
}
