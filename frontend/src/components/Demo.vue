<template>
	<div class="m-32 flex flex-col gap-6">
		<EditorContent
			class="border"
			:class="{
				'border-gray-200': !editor?.isEditable,
			}"
			:editor="editor"
			@dblclick="toggleEditable"
			@blur="toggleEditable"
		/>
		<div class="flex justify-between">
			<Button label="Toggle Bold" @click="toggleTextStyle('bold')" />
			<Button label="Toggle Italic" @click="toggleTextStyle('italic')" />
			<Button label="Toggle Underline" @click="toggleTextStyle('underline')" />
			<Button label="Toggle Strike" @click="toggleTextStyle('strike')" />
			<Button label="Toggle Bullets" @click="toggleList" />
			<Button label="Change Text Style" @click="changeTextStyle" />
		</div>
	</div>
</template>

<script setup>
import { EditorContent, useEditor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import TextStyle from '@tiptap/extension-text-style'
import Paragraph from '@tiptap/extension-paragraph'
import Underline from '@tiptap/extension-underline'
import BulletList from '@tiptap/extension-bullet-list'
import OrderedList from '@tiptap/extension-ordered-list'

const CustomTextStyle = TextStyle.extend({
	addAttributes() {
		return {
			fontSize: {
				default: null,
				parseHTML: (el) => el.style.fontSize || null,
				renderHTML: (attrs) =>
					attrs.fontSize ? { style: `font-size: ${attrs.fontSize}` } : {},
			},
			fontFamily: {
				default: null,
				parseHTML: (el) => el.style.fontFamily || null,
				renderHTML: (attrs) =>
					attrs.fontFamily ? { style: `font-family: ${attrs.fontFamily}` } : {},
			},
			color: {
				default: null,
				parseHTML: (el) => el.style.color || null,
				renderHTML: (attrs) => (attrs.color ? { style: `color: ${attrs.color}` } : {}),
			},
		}
	},
})

const CustomParagraph = Paragraph.extend({
	addAttributes() {
		return {
			fontSize: {
				default: null,
				parseHTML: (element) => element.style.fontSize || null,
				renderHTML: (attributes) => {
					if (!attributes.fontSize) return {}
					return {
						style: `font-size: ${attributes.fontSize}`,
					}
				},
			},
			fontFamily: {
				default: null,
				parseHTML: (el) => el.style.fontFamily || null,
				renderHTML: (attrs) =>
					attrs.fontFamily ? { style: `font-family: ${attrs.fontFamily}` } : {},
			},
			color: {
				default: null,
				parseHTML: (el) => el.style.color || null,
				renderHTML: (attrs) => (attrs.color ? { style: `color: ${attrs.color}` } : {}),
			},
		}
	},
})

const editor = useEditor({
	extensions: [
		StarterKit.configure({
			paragraph: false,
			bulletList: false,
			orderedList: false,
		}),
		BulletList.configure({
			HTMLAttributes: {
				class: 'list-disc pl-6',
			},
		}),
		OrderedList.configure({
			HTMLAttributes: {
				class: 'list-decimal pl-6',
			},
		}),
		CustomTextStyle,
		CustomParagraph,
		Underline,
	],
	content: `
        <p>This is a bullet list test</p>
        <p>Put cursor here and click the button</p>
    `,
})

const toggleEditable = () => {
	editor.value.setEditable(!editor.value.isEditable)
}

const changeTextStyle = () => {
	editor.value
		.chain()
		.focus()
		.setNode('paragraph', {
			fontSize: '48px',
			fontFamily: 'Arial',
			color: '#333',
		})
		.run()
}

const toggleTextStyle = (style) => {
	const { state, view } = editor.value
	const { selection } = state

	if (selection.empty) {
		// Nothing selected — expand to entire parent node
		const { $from } = selection
		const node = $from.node($from.depth) // current block node
		const pos = $from.start($from.depth)
		const end = pos + node.nodeSize - 2

		if (style === 'bold')
			editor.value.chain().focus().setTextSelection({ from: pos, to: end }).toggleBold().run()
		else if (style === 'italic')
			editor.value
				.chain()
				.focus()
				.setTextSelection({ from: pos, to: end })
				.toggleItalic()
				.run()
		else if (style === 'underline')
			editor.value
				.chain()
				.focus()
				.setTextSelection({ from: pos, to: end })
				.toggleUnderline()
				.run()
		else if (style === 'strike')
			editor.value
				.chain()
				.focus()
				.setTextSelection({ from: pos, to: end })
				.toggleStrike()
				.run()
	} else {
		if (style === 'bold') editor.value.chain().focus().toggleBold().run()
		else if (style === 'italic') editor.value.chain().focus().toggleItalic().run()
		else if (style === 'underline') editor.value.chain().focus().toggleUnderline().run()
		else if (style === 'strike') editor.value.chain().focus().toggleStrike().run()
	}
}

const toggleList = () => {
	editor.value.chain().focus().toggleOrderedList().run()
}
</script>
