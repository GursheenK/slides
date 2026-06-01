<template>
	<div
		class="table-element h-full w-full"
		:style="{ '--cell-border': cellBorder }"
		@mousedown="handleMouseDown"
		@dblclick="handleDoubleClick"
	>
		<EditorContent v-if="showEditor" :editor="editor" class="h-full w-full" />
		<div
			v-else
			v-html="element.content"
			class="h-full w-full select-none"
			:class="{ 'cursor-text': isSelected }"
			@click="handleStaticClick"
		/>
	</div>
</template>

<script setup>
import { computed, watchEffect, shallowRef, nextTick } from 'vue'
import { Editor, EditorContent } from '@tiptap/vue-3'

import { tableExtensions } from '@/stores/tiptapSetup'
import { activeElementIds, focusElementId } from '@/stores/element'
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

const showEditor = computed(
	() => focusElementId.value === element.value.id && props.mode === 'editor',
)

const editor = shallowRef(null)
let contentSnapshot = null

watchEffect((onCleanup) => {
	if (!showEditor.value) return

	const instance = new Editor({
		content: element.value.content,
		extensions: tableExtensions,
		editable: true,
		editorProps: { attributes: { class: 'outline-none h-full w-full' } },
	})

	instance.on('focus', () => {
		contentSnapshot = instance.getHTML()
	})
	instance.on('blur', () => {
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

	editor.value = instance

	onCleanup(() => {
		instance.destroy()
		editor.value = null
		contentSnapshot = null
	})
})

const focusAtCoords = ({ clientX, clientY }) => {
	if (!editor.value) return
	const pos = editor.value.view.posAtCoords({ left: clientX, top: clientY })
	if (pos) {
		editor.value.chain().focus().setTextSelection(pos.pos).run()
	} else {
		editor.value.commands.focus()
	}
}

const enterEditMode = async (e) => {
	const { clientX, clientY } = e
	focusElementId.value = element.value.id
	await nextTick() // wait for EditorContent to mount and schedule its internal nextTick
	await nextTick() // wait for EditorContent's nextTick to append view.dom to the document
	focusAtCoords({ clientX, clientY })
}

const handleDoubleClick = (e) => {
	if (props.mode !== 'editor') return
	e.stopPropagation()
	emit('clearTimeouts')
	activeElementIds.value = [element.value.id]
	enterEditMode(e)
}

// Single click on already-selected table: enter edit mode
// e.detail >= 2 means this click is part of a dblclick — skip it, handleDoubleClick handles that
const handleStaticClick = (e) => {
	if (e.detail >= 2 || !isSelected.value || props.mode !== 'editor') return
	enterEditMode(e)
}

const handleMouseDown = (e) => {
	const isColumnResize = editor.value?.view.dom.classList.contains('resize-cursor')
	if (isColumnResize || isSelected.value) e.stopPropagation()
}

const cellBorder = computed(
	() => `${element.value.borderWidth}px solid ${element.value.borderColor}`,
)
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
	vertical-align: top;
}
.table-element p:empty::before {
	content: '\200B';
}
.table-element .ProseMirror td,
.table-element .ProseMirror th {
	cursor: text;
}
</style>
