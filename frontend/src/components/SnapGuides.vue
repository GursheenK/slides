<template>
	<div v-for="guide in Object.keys(guideStyles)" :key="guide" :style="guideStyles[guide]"></div>
</template>

<script setup>
import { computed } from 'vue'

import { slideBounds, selectionBounds, guideVisibilityMap } from '@/stores/slide'
import { pairElementId } from '@/stores/element'
import { getElementDiv } from '@/stores/elementRegistry'

const props = defineProps({
	visibilityMap: {
		type: Object,
		default: null,
	},
	ongoingInteraction: {
		type: Boolean,
		default: false,
	},
})

const commonStyles = {
	position: 'absolute',
	zIndex: 9999,
}

const isVisible = (axis) => {
	const closeToSnap = props.ongoingInteraction && props.visibilityMap?.[axis]
	const hoveringOverControl = guideVisibilityMap[axis]
	return closeToSnap || hoveringOverControl
}

const getCenterStyles = (axis) => {
	return {
		...commonStyles,
		backgroundColor: '#70b6f080',
		width: axis === 'centerY' ? '1px' : '100%',
		height: axis === 'centerX' ? '1px' : '100%',
		left: axis === 'centerY' ? '50%' : '0',
		top: axis === 'centerX' ? '50%' : '0',
		display: isVisible(axis) ? 'block' : 'none',
	}
}

const getScaledValue = (value, axis) => {
	if (axis == 'X') return (value - slideBounds.left) / slideBounds.scale
	return (value - slideBounds.top) / slideBounds.scale
}

// computed so the paired element is measured once per pairing (it cannot move
// mid-gesture), not on every re-render during the interaction
const pairedBounds = computed(() => {
	const div = getElementDiv(pairElementId.value)
	if (!div) return null

	const rect = div.getBoundingClientRect()
	return {
		left: getScaledValue(rect.left, 'X'),
		top: getScaledValue(rect.top, 'Y'),
		right: getScaledValue(rect.right, 'X'),
		bottom: getScaledValue(rect.bottom, 'Y'),
		height: rect.height / slideBounds.scale,
		width: rect.width / slideBounds.scale,
	}
})

const getVerticalStyles = (direction) => {
	if (!pairedBounds.value || !props.visibilityMap[direction]) return ''

	const { top: pairedTop, height: pairedHeight } = pairedBounds.value

	const left =
		direction == 'left'
			? selectionBounds.left - 1
			: selectionBounds.left + selectionBounds.width
	const top = Math.min(selectionBounds.top, pairedTop)
	const lastElementHeight =
		pairedTop < selectionBounds.top ? selectionBounds.height : pairedHeight
	const height = Math.abs(pairedTop - selectionBounds.top) + lastElementHeight

	return {
		...commonStyles,
		borderColor: '#70b6f080',
		borderStyle: 'dashed',
		borderWidth: '0 0 0 1px',
		left: `${left}px`,
		top: `${top}px`,
		height: `${height}px`,
		display: isVisible(direction) ? 'block' : 'none',
	}
}

const getHorizontalStyles = (direction) => {
	if (!pairedBounds.value || !props.visibilityMap[direction]) return ''

	const { left: pairedLeft, width: pairedWidth } = pairedBounds.value

	const top =
		direction == 'top' ? selectionBounds.top - 1 : selectionBounds.top + selectionBounds.height
	const left = Math.min(selectionBounds.left, pairedLeft)

	const lastElementWidth = pairedLeft < selectionBounds.left ? selectionBounds.width : pairedWidth
	const width = Math.abs(pairedLeft - selectionBounds.left) + lastElementWidth

	return {
		...commonStyles,
		borderColor: '#70b6f080',
		borderStyle: 'dashed',
		borderWidth: '1px 0 0 0',
		top: `${top}px`,
		left: `${left}px`,
		width: `${width}px`,
		display: isVisible(direction) ? 'block' : 'none',
	}
}

const getEdgeStyles = (direction) => {
	return {
		...commonStyles,
		width: ['leftEdge', 'rightEdge'].includes(direction) ? '1.5px' : '100%',
		height: ['topEdge', 'bottomEdge'].includes(direction) ? '1.5px' : '100%',
		left: direction == 'rightEdge' ? `calc(100% - 1.5px)` : '0%',
		top: direction == 'bottomEdge' ? `calc(100% - 1.5px)` : '0%',
		display: isVisible(direction) ? 'block' : 'none',
	}
}

const guideStyles = computed(() => {
	return {
		centerX: getCenterStyles('centerX'),
		centerY: getCenterStyles('centerY'),
		left: getVerticalStyles('left'),
		right: getVerticalStyles('right'),
		top: getHorizontalStyles('top'),
		bottom: getHorizontalStyles('bottom'),
		leftEdge: getEdgeStyles('leftEdge'),
		rightEdge: getEdgeStyles('rightEdge'),
		topEdge: getEdgeStyles('topEdge'),
		bottomEdge: getEdgeStyles('bottomEdge'),
	}
})
</script>
