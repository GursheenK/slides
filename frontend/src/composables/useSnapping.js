import { reactive, computed, watch } from 'vue'
import { selectionBounds, currentSlide, slideBounds } from '../stores/slide'
import { activeElementIds, pairElementId } from '../stores/element'
import { getElementDiv } from '../stores/elementRegistry'

export const useSnapping = (target, parent, currentResizer, hasOngoingInteraction) => {
	const RELEASE_FACTOR = 1.25

	// engaged guide per channel: 'x' snaps to vertical guides, 'y' to horizontal
	const engaged = reactive({ x: null, y: null })

	// rects of non-active elements, snapshotted once per gesture — they cannot
	// move mid-gesture, and reading layout per mousemove forces synchronous reflow
	const staticElementRects = new Map()

	const cacheStaticElementRects = () => {
		staticElementRects.clear()

		currentSlide.value?.elements.forEach((element) => {
			if (activeElementIds.value.includes(element.id)) return

			const elementDiv = getElementDiv(element.id)
			if (!elementDiv) return

			const rect = elementDiv.getBoundingClientRect()
			staticElementRects.set(element.id, {
				left: rect.left,
				right: rect.right,
				top: rect.top,
				bottom: rect.bottom,
			})
		})
	}

	watch(hasOngoingInteraction, (ongoing) => {
		if (ongoing) return cacheStaticElementRects()

		staticElementRects.clear()
		engaged.x = null
		engaged.y = null
	})

	// pan/zoom mid-gesture moves the cached rects on screen — resnapshot
	watch(
		() => [slideBounds.left, slideBounds.top, slideBounds.scale],
		() => {
			if (hasOngoingInteraction.value) cacheStaticElementRects()
		},
	)

	// engage threshold in viewport px, sized to the selection
	const getThreshold = () => {
		const scaledHeight = selectionBounds.height * slideBounds.scale * 0.1
		const minThreshold = scaledHeight > 50 ? scaledHeight / 6 : scaledHeight / 5
		const maxThreshold = scaledHeight > 50 ? scaledHeight / 4 : scaledHeight / 3
		return Math.max(minThreshold, Math.min(maxThreshold, scaledHeight))
	}

	// guides only show while actually snapped
	const visibilityMap = computed(() => {
		if (!hasOngoingInteraction.value) return {}

		return {
			centerY: engaged.x?.guide === 'centerY',
			left: engaged.x?.guide === 'left',
			right: engaged.x?.guide === 'right',
			centerX: engaged.y?.guide === 'centerX',
			top: engaged.y?.guide === 'top',
			bottom: engaged.y?.guide === 'bottom',
		}
	})

	const slideCenter = () => ({
		x: slideBounds.left + slideBounds.width / 2,
		y: slideBounds.top + slideBounds.height / 2,
	})

	const toViewport = (rect) => {
		const scale = slideBounds.scale
		const left = slideBounds.left + rect.left * scale
		const top = slideBounds.top + rect.top * scale

		return {
			left,
			top,
			right: left + rect.width * scale,
			bottom: top + rect.height * scale,
		}
	}

	// pair with the first cached element that has a like-edge near the desired
	// rect; drives the pair highlight + the edge guide candidates
	const updatePairing = (vp) => {
		const threshold = getThreshold()

		for (const [id, bounds] of staticElementRects) {
			const isNear =
				Math.abs(vp.left - bounds.left) < threshold ||
				Math.abs(vp.right - bounds.right) < threshold ||
				Math.abs(vp.top - bounds.top) < threshold ||
				Math.abs(vp.bottom - bounds.bottom) < threshold

			if (isNear) {
				pairElementId.value = id
				return bounds
			}
		}

		pairElementId.value = null
		return null
	}

	// keep the engaged guide while desired stays inside the release window,
	// otherwise engage the nearest candidate inside the engage threshold
	const chooseGuide = (channel, candidates) => {
		const current = engaged[channel]

		if (current) {
			const held = candidates.find((c) => c.guide === current.guide && c.id === current.id)
			if (held && Math.abs(held.offset) < held.threshold * RELEASE_FACTOR) {
				return held
			}
		}

		const within = candidates.filter((c) => Math.abs(c.offset) < c.threshold)
		within.sort((a, b) => Math.abs(a.offset) - Math.abs(b.offset))

		return within[0] || null
	}

	const snapChannel = (channel, candidates) => {
		const chosen = chooseGuide(channel, candidates)
		engaged[channel] = chosen ? { guide: chosen.guide, id: chosen.id } : null
		return chosen ? chosen.offset : 0
	}

	const translationCandidates = (vp, paired) => {
		const threshold = getThreshold()
		const center = slideCenter()

		const x = [
			{
				guide: 'centerY',
				id: 'slide',
				offset: center.x - (vp.left + vp.right) / 2,
				threshold,
			},
		]
		const y = [
			{
				guide: 'centerX',
				id: 'slide',
				offset: center.y - (vp.top + vp.bottom) / 2,
				threshold,
			},
		]

		if (paired) {
			const id = pairElementId.value
			x.push({ guide: 'left', id, offset: paired.left - vp.left, threshold })
			x.push({ guide: 'right', id, offset: paired.right - vp.right, threshold })
			y.push({ guide: 'top', id, offset: paired.top - vp.top, threshold })
			y.push({ guide: 'bottom', id, offset: paired.bottom - vp.bottom, threshold })
		}

		return { x, y }
	}

	const edgeCandidates = (vp, paired) => {
		const threshold = getThreshold()
		const center = slideCenter()
		const resizer = currentResizer.value || ''
		const id = pairElementId.value

		const x = []
		const y = []

		if (resizer.includes('left')) {
			x.push({ guide: 'centerY', id: 'slide', offset: center.x - vp.left, threshold })
			if (paired) x.push({ guide: 'left', id, offset: paired.left - vp.left, threshold })
		} else if (resizer.includes('right')) {
			x.push({ guide: 'centerY', id: 'slide', offset: center.x - vp.right, threshold })
			if (paired) x.push({ guide: 'right', id, offset: paired.right - vp.right, threshold })
		}

		if (resizer.includes('top')) {
			y.push({ guide: 'centerX', id: 'slide', offset: center.y - vp.top, threshold })
			if (paired) y.push({ guide: 'top', id, offset: paired.top - vp.top, threshold })
		} else if (resizer.includes('bottom')) {
			y.push({ guide: 'centerX', id: 'slide', offset: center.y - vp.bottom, threshold })
			if (paired)
				y.push({ guide: 'bottom', id, offset: paired.bottom - vp.bottom, threshold })
		}

		return { x, y }
	}

	// rect is the desired geometry in slide units; returns it with snapping applied
	const applySnapping = (rect, interaction, { axes = ['x', 'y'] } = {}) => {
		if (!target.value || !hasOngoingInteraction.value) return rect

		const scale = slideBounds.scale
		const vp = toViewport(rect)
		const paired = updatePairing(vp)

		if (interaction === 'dragging') {
			const candidates = translationCandidates(vp, paired)
			const dx = snapChannel('x', candidates.x) / scale
			const dy = snapChannel('y', candidates.y) / scale

			return { ...rect, left: rect.left + dx, top: rect.top + dy }
		}

		const candidates = edgeCandidates(vp, paired)
		const dx = axes.includes('x') ? snapChannel('x', candidates.x) / scale : 0
		const dy = axes.includes('y') ? snapChannel('y', candidates.y) / scale : 0

		const resizer = currentResizer.value || ''
		const snapped = { ...rect }

		// only the moving edge takes the offset; the opposite edge stays put
		if (resizer.includes('left')) {
			snapped.left += dx
			snapped.width -= dx
		} else if (resizer.includes('right')) {
			snapped.width += dx
		}

		if (resizer.includes('top')) {
			snapped.top += dy
			snapped.height -= dy
		} else if (resizer.includes('bottom')) {
			snapped.height += dy
		}

		return snapped
	}

	return { visibilityMap, applySnapping }
}
