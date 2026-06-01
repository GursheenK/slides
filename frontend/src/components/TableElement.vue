<template>
	<div :style="containerStyles" class="table-element relative">
		<!-- Editor — always mounted so columnResizing plugin stays active -->
		<div class="table-editor h-full w-full" @mousedown="handleMouseDown">
			<EditorContent v-if="editor" :editor="editor" class="h-full w-full" />
		</div>

		<!-- Overlay — only when table is not selected, so clicks select the element normally -->
		<div v-if="!isSelected" class="absolute inset-0" @dblclick="handleDoubleClick" />
	</div>
</template>

<script setup>
import { computed, watch, onBeforeUnmount, inject, ref } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'

import { tableExtensions } from '@/stores/tiptapSetup'
import { commandHistory } from '@/stores/historyMeta'
import { editElementCommand } from '@/stores/commands'
import { currentSlide } from '@/stores/slide'
import {
	activeElementIds,
	focusElementId,
	focusTableCell,
	activeTableEditor,
} from '@/stores/element'

const props = defineProps({
	mode: { type: String, default: 'editor' },
	elementOffset: { type: Object, default: () => ({ left: 0, top: 0 }) },
	transitionStyles: { type: Object, default: () => ({}) },
})

const element = defineModel('element', { type: Object, default: null })
const emit = defineEmits(['clearTimeouts'])

const inSlideShowMode = inject('inSlideShowMode', ref(false))
const inReadonlyMode = inject('inReadonlyMode', ref(false))

const isSelected = computed(() => activeElementIds.value.includes(element.value.id))
const isInEditMode = computed(
	() => focusElementId.value === element.value.id && props.mode === 'editor',
)

// — CSS v-bind values (used in <style scoped> below) —
const cellBorder = computed(
	() => `${element.value.borderWidth}px solid ${element.value.borderColor}`,
)
const rowHeight = computed(() => `${(100 / element.value.rows).toFixed(4)}%`)
const opacity = computed(() => (element.value.opacity || 100) / 100)

// — Editor —

const editor = useEditor({
	content: element.value.content,
	extensions: tableExtensions,
	editable: true, // always true so columnResizing plugin is registered at creation
	editorProps: {
		attributes: { class: 'outline-none h-full w-full' },
	},
})

watch(isInEditMode, (val) => {
	if (!val) activeTableEditor.value = null
})

// — Undo / redo — snapshot on focus, commit on blur —

let contentSnapshot = null

watch(
	editor,
	(e) => {
		if (!e) return

		e.on('focus', () => {
			contentSnapshot = e.getHTML()
			activeTableEditor.value = e
		})

		e.on('blur', () => {
			const newContent = e.getHTML()
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
			focusTableCell.value = null
			activeTableEditor.value = null
		})

		e.on('selectionUpdate', ({ editor: ed }) => {
			focusTableCell.value = ed.isActive('table') ? { elementId: element.value.id } : null
		})
	},
	{ immediate: true },
)

// — Header row toggle — sync from element JSON into TipTap —

watch(
	() => element.value.headerRow,
	(newVal, oldVal) => {
		if (newVal !== oldVal && editor.value?.isEditable) {
			editor.value.chain().focus().toggleHeaderRow().run()
		}
	},
)

// — Interaction handlers —

const handleMouseDown = (e) => {
	// Column resize — stop propagation so SlideContainer drag doesn't fire
	if (editor.value?.view.dom.classList.contains('resize-cursor')) {
		e.stopPropagation()
		return
	}
	// Single click when selected — enter edit mode, let TipTap place the cursor
	if (isSelected.value && props.mode === 'editor' && !inReadonlyMode.value) {
		e.stopPropagation()
		focusElementId.value = element.value.id
		return
	}
	if (isInEditMode.value) {
		e.stopPropagation()
	}
}

const handleDoubleClick = (e) => {
	if (inSlideShowMode.value || inReadonlyMode.value) return
	emit('clearTimeouts')
	activeElementIds.value = [element.value.id]
	focusElementId.value = element.value.id
}

// — Container styles —

const containerStyles = computed(() => ({
	width: '100%',
	height: '100%',
	...props.transitionStyles,
}))

// — Cleanup —

onBeforeUnmount(() => {
	if (activeTableEditor.value === editor.value) activeTableEditor.value = null
	editor.value?.destroy()
})
</script>

<style scoped>
.table-element {
	opacity: v-bind(opacity);
}

.table-editor :deep(.ProseMirror) {
	margin: 0;
	padding: 0;
	height: 100%;
}

.table-editor :deep(.tableWrapper) {
	height: 100%;
	overflow: visible;
}

.table-editor :deep(table) {
	border-collapse: collapse;
	table-layout: fixed;
	width: 100%;
	height: 100%;
	margin: 0;
}

.table-editor :deep(tr) {
	height: v-bind(rowHeight);
}

.table-editor :deep(td),
.table-editor :deep(th) {
	border: v-bind(cellBorder);
	padding: 4px 8px;
	min-width: 20px;
	vertical-align: top;
	position: relative;
	box-sizing: border-box;
	background-color: transparent;
	font-weight: normal;
	text-align: left;
}

.table-editor :deep(td p),
.table-editor :deep(th p) {
	margin: 0;
	padding: 0;
}

/* Hide trailing <br> only when there's real content before it */
.table-editor :deep(td .ProseMirror-trailingBreak:not(:first-child)),
.table-editor :deep(th .ProseMirror-trailingBreak:not(:first-child)) {
	display: none;
}

.table-editor :deep(.column-resize-handle) {
	position: absolute;
	right: -2px;
	top: 0;
	bottom: 0;
	width: 4px;
	background-color: #93c5fd;
	z-index: 20;
}

.table-editor :deep(.resize-cursor) {
	cursor: col-resize;
}
</style>
