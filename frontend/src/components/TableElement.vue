<template>
	<div
		class="table-element h-full w-full"
		:style="{
			'--cell-border': cellBorder,
			'--border-width': `${element.value?.borderWidth || 0}px`,
			'--row-height': rowHeight,
			'--cell-text-color': element.textColor,
			opacity: element.opacity / 100,
		}"
		@mousedown="handleMouseDown"
		@dblclick="handleDoubleClick"
	>
		<EditorContent v-if="showEditor" :editor="editor" class="h-full w-full" />
		<div v-else v-html="element.content" class="h-full w-full select-none" />
	</div>
</template>

<script setup>
import { computed, watch, shallowRef } from 'vue'
import { Editor, EditorContent } from '@tiptap/vue-3'

import { tableExtensions } from '@/stores/tiptapSetup'
import { activeElementIds, focusElementId, activeTableEditor } from '@/stores/element'
import { currentSlide } from '@/stores/slide'
import { commandHistory } from '@/stores/historyMeta'
import { editElementCommand } from '@/stores/commands'

const props = defineProps({
	mode: { type: String, default: 'editor' },
	elementOffset: { type: Object, default: () => ({ left: 0, top: 0 }) },
	transitionStyles: { type: Object, default: () => ({}) },
})

const element = defineModel('element', { type: Object, default: null })
const emit = defineEmits(['clearTimeouts'])

const isSelected = computed(() => activeElementIds.value.includes(element.value.id))

// Editor mounts only while the table is selected — on-the-fly like TextElement.
const showEditor = computed(() => isSelected.value && props.mode === 'editor')

const editor = shallowRef(null)
let contentSnapshot = null

watch(
	showEditor,
	(show, _, onCleanup) => {
		if (!show) return

		const instance = new Editor({
			content: element.value.content,
			extensions: tableExtensions,
			editable: true,
			editorProps: { attributes: { class: 'outline-none h-full w-full' } },
		})

		instance.on('focus', () => {
			focusElementId.value = element.value.id
			contentSnapshot = instance.getHTML()
		})
		instance.on('blur', () => {
			focusElementId.value = null
			const newContent = instance.getHTML()
			if (contentSnapshot !== null && newContent !== contentSnapshot) {
				commandHistory.execute(
					editElementCommand({
						slideId: currentSlide.value.clientId,
						elementIds: [element.value.id],
						property: 'content',
						oldValue: contentSnapshot,
						newValue: newContent,
					}),
				)
			}
			contentSnapshot = null
		})

		// Sync element.content → editor when changed externally (app undo/redo)
		const stopContentSync = watch(
			() => element.value.content,
			(newContent) => {
				if (newContent !== instance.getHTML()) {
					instance.commands.setContent(newContent, false)
				}
			},
		)

		editor.value = instance
		activeTableEditor.value = instance

		onCleanup(() => {
			stopContentSync()
			// Commit any content change that wasn't captured by blur (e.g. col resizing,
			// which prevents default on mousedown so the editor never receives focus).
			const finalContent = instance.getHTML()
			if (finalContent !== element.value.content) {
				commandHistory.execute(
					editElementCommand({
						slideId: currentSlide.value.clientId,
						elementIds: [element.value.id],
						property: 'content',
						oldValue: element.value.content,
						newValue: finalContent,
					}),
				)
			}
			instance.destroy()
			editor.value = null
			activeTableEditor.value = null
			contentSnapshot = null
		})
	},
	{ immediate: true },
)

const handleDoubleClick = (e) => {
	if (props.mode !== 'editor') return
	e.stopPropagation()
}

const handleMouseDown = (e) => {
	const isColumnResize = editor.value?.view.dom.classList.contains('resize-cursor')
	if (isColumnResize || isSelected.value) e.stopPropagation()
}

const cellBorder = computed(
	() => `${element.value.borderWidth}px solid ${element.value.borderColor}`,
)

const rowHeight = computed(() => {
	const liveHeight = element.value.height + (props.elementOffset.height ?? 0)
	const rows = element.value.rows || 1
	const borderWidth = element.value.borderWidth || 0
	// (rows+1) border slots: outer top + (rows-1) internal + outer bottom
	const totalBorderHeight = (rows + 1) * borderWidth
	return `${(liveHeight - totalBorderHeight) / rows}px`
})
</script>

<style>
.table-element .tableWrapper {
	height: 100%;
}
.table-element table {
	border-collapse: collapse;
	table-layout: fixed;
	width: 100%;
	height: 100%;
}
.table-element td,
.table-element th {
	border: var(--cell-border);
	padding: 0.5rem;
	/* min width is needed because col resizing shouldn't collapse two columns into same boundary */
	min-width: 1px;
	word-break: break-word;
	position: relative;
	font-family: 'Inter', sans-serif;
	font-size: 20px;
	color: var(--cell-text-color);
}
.table-element th {
	background-color: #e5e7eb;
}
.table-element .column-resize-handle {
	position: absolute;
	right: -2px;
	top: 0;
	bottom: 0;
	width: 4px;
	background-color: #70b6f0;
	pointer-events: none;
	z-index: 20;
}
.table-element .resize-cursor {
	cursor: col-resize;
}
.table-element .cell-content {
	/* subtract td's top + bottom padding so td height stays exactly --row-height */
	height: calc(var(--row-height) - 1rem);
	overflow: hidden;
}
.table-element p:empty::before {
	content: '\200B';
}
.table-element .ProseMirror td,
.table-element .ProseMirror th {
	cursor: text;
}
.table-element .resize-cursor td,
.table-element .resize-cursor th {
	cursor: col-resize;
}
</style>
