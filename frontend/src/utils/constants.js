const sectionClasses = 'flex flex-col p-3 border-b'
const sectionTitleClasses = 'text-base font-medium text-gray-800'
const fieldLabelClasses = 'text-sm text-gray-600'

const allowedImageFileTypes = [
	'image/jpeg',
	'image/jpg',
	'image/png',
	'image/gif',
	'image/webp',
	'image/svg+xml',
]

const minElementSizes = {
	text: { width: 7, height: 7 },
	shape: { width: 10, height: 16 },
	image: { width: 20, height: 20 },
	video: { width: 20, height: 20 },
	default: { width: 10, height: 16 },
}

export {
	sectionClasses,
	sectionTitleClasses,
	fieldLabelClasses,
	allowedImageFileTypes,
	minElementSizes,
}
