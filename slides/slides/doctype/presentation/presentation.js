// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Presentation", {
	refresh(frm) {
		frm.add_custom_button("Optimize Videos", () => {
			frappe.call({
				method: "slides.slides.doctype.presentation.presentation.convert_videos_to_webm",
				args: {
					docname: frm.doc.name,
				},
				callback: function (r) {
					if (!r.exc) {
						frappe.msgprint("Video conversion completed!");
						frm.reload_doc();
					}
				},
			});
		});
	},
});
