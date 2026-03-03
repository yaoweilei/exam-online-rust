/*---------------------------------------------------------------------------------------------
 *  Copyright (c) 2025 Yaoweilei. All rights reserved.
 *
 *  This software is proprietary and confidential.
 *  Unauthorized copying, distribution, modification, or use of this software,
 *  via any medium, is strictly prohibited without prior written permission.
 *--------------------------------------------------------------------------------------------*/

/**
 * 分类导航管理器 - 负责分类下拉菜单和导航
 */
class CategoryNavigationManager {
	constructor(examViewer) {
		this.examViewer = examViewer;
	}

	/**
	 * 初始化分类下拉菜单
	 */
	initCategoryDropdowns() {
		console.log('[CategoryNavigationManager] initCategoryDropdowns called');
		const categorySlots = document.querySelectorAll('.category-slot');
		console.log('[CategoryNavigationManager] Found category slots:', categorySlots.length);

		categorySlots.forEach((slot, index) => {
			slot.querySelectorAll('.category-multi-dropdown').forEach(n => n.remove());
			const catType = slot.getAttribute('data-cat-slot');
			console.log(`[CategoryNavigationManager] Processing slot ${index} with type:`, catType);
			if (!catType) { return; }

			const dropdown = document.createElement('div');
			dropdown.className = 'category-multi-dropdown';

			const label = document.createElement('div');
			label.className = 'category-dropdown-label';
			label.textContent = this.getCategoryDisplayName(catType);
			label.addEventListener('click', () => {
				this.toggleCategoryDropdown(dropdown);
			});

			const menu = document.createElement('div');
			menu.className = 'category-dropdown-menu';

			const menuItems = this.getCategoryMenuItems(catType);
			console.log(`[CategoryNavigationManager] Menu items for ${catType}:`, menuItems);
			menuItems.forEach(item => {
				const menuItem = document.createElement('div');
				menuItem.className = 'category-menu-item';
				menuItem.textContent = item.label;
				menuItem.addEventListener('click', () => {
					this.selectCategoryItem(catType, item.value);
					this.closeCategoryDropdown(dropdown);
				});
				menu.appendChild(menuItem);
			});

			dropdown.appendChild(label);
			dropdown.appendChild(menu);
			slot.appendChild(dropdown);
			console.log(`[CategoryNavigationManager] Dropdown created for slot ${index}`);
		});

		if (!document.__exam_category_click_registered) {
			document.addEventListener('click', (e) => {
				if (!e.target.closest('.category-multi-dropdown')) {
					document.querySelectorAll('.category-multi-dropdown.open').forEach(dropdown => {
						dropdown.classList.remove('open');
					});
				}
			});
			document.__exam_category_click_registered = true;
		}
	}

	/**
	 * 渲染分类导航
	 */
	renderCategoryNavigation() {
		const container = DOMUtils.safeGetElement("category-navigation", "renderCategoryNavigation");
		if (!container || !this.examViewer.currentExam) { return; }

		DOMUtils.safeSetInnerHTML(container, "", "renderCategoryNavigation-clear");

		const categories = this.examViewer.getCategories();
		const categoryMap = new Map(categories.map((c) => [c.id, c]));

		const order = [
			{ id: "vocab", label: "词汇/语法" },
			{ id: "reading", label: "阅读" },
			{ id: "listening", label: "听力" }
		];

		order.forEach((def) => {
			const data = categoryMap.get(def.id);
			if (!data) { return; }

			const wrap = DOMUtils.createElementWithClass("div", "category-multi-dropdown");

			const label = DOMUtils.createElementWithClass("div", "category-dropdown-label");
			label.textContent = def.label;
			label.addEventListener("click", (e) => {
				e.stopPropagation();
				wrap.classList.toggle("open");
			});

			const menu = DOMUtils.createElementWithClass("div", "category-dropdown-menu");

			data.sectionIndexes.forEach((sectionIdx) => {
				const section = this.examViewer.currentExam.exam_info.sections[sectionIdx];
				if (!section || !section.questions || !section.questions.length) { return; }

				const item = document.createElement("div");
				item.className = "category-menu-item";

				let labelText = "";
				const rawName = (section.section_name || section.section_title || "").trim().replace(/\s+/g, '');
				const m = rawName.match(/^(問題\d+)/);
				if (m) {
					labelText = m[1];
				} else {
					const fallbackId = section.questions.reduce((acc, q) => q.id < acc ? q.id : acc, section.questions[0].id);
					labelText = `問題${fallbackId}`;
				}

				item.textContent = labelText;
				item.title = rawName;
				item.dataset.categoryId = def.id;
				item.dataset.sectionIndex = sectionIdx;

				item.addEventListener("click", (ev) => {
					ev.stopPropagation();
					this.examViewer.stateManager.updateNavigationState(sectionIdx, 0, def.id);
					wrap.classList.remove("open");

					const ql = document.getElementById("question-list");
					if (ql) { ql.classList.add("hidden"); }
				});

				menu.appendChild(item);
			});

			wrap.appendChild(label);
			wrap.appendChild(menu);
			container.appendChild(wrap);
		});

		document.addEventListener("click", () => {
			Array.from(container.querySelectorAll(".category-multi-dropdown")).forEach((el) => el.classList.remove("open"));
		});
	}

	/**
	 * 获取分类显示名称
	 */
	getCategoryDisplayName(catType) {
		const names = {
			'vocab': '词汇',
			'reading': '阅读',
			'listening': '听力'
		};
		return names[catType] || catType;
	}

	/**
	 * 获取分类菜单项
	 */
	getCategoryMenuItems(catType) {
		if (!this.examViewer.currentExam) {
			return [];
		}

		const sections = this.examViewer.currentExam.exam_info?.sections || [];
		const items = [];

		const categories = this.examViewer.getCategories();
		const category = categories.find(cat => cat.id === catType);
		if (category && category.sectionIndexes.length > 0) {
			category.sectionIndexes.forEach((sectionIndex) => {
				const section = sections[sectionIndex];
				if (section) {
					let label = section.section_name || section.section_title;
					if (label) {
						label = label.replace(/\s+/g, '');
					}
					if (!label) {
						const sectionId = section.section_id;
						if (typeof sectionId === 'number') {
							if (sectionId >= 1.01 && sectionId <= 1.06) {
								label = `词汇${sectionId}`;
							} else if (sectionId >= 1.07 && sectionId <= 1.99) {
								label = `阅读${sectionId}`;
							} else if (Math.floor(sectionId) === 2) {
								label = `听力${sectionId}`;
							} else {
								label = `问题${sectionId}`;
							}
						} else {
							label = `第${sectionIndex + 1}部分`;
						}
					}
					items.push({
						label: label,
						value: `section-${sectionIndex}`
					});
				}
			});
		} else {
			sections.forEach((section, index) => {
				let label = section.section_name || section.section_title;
				if (label) {
					label = label.replace(/\s+/g, '');
				}
				if (!label) {
					label = `第${index + 1}部分`;
				}
				items.push({
					label: label,
					value: `section-${index}`
				});
			});
		}

		return items;
	}

	/**
	 * 切换分类下拉菜单
	 */
	toggleCategoryDropdown(dropdown) {
		const isOpen = dropdown.classList.contains('open');
		document.querySelectorAll('.category-multi-dropdown.open').forEach(d => {
			d.classList.remove('open');
		});
		if (!isOpen) {
			dropdown.classList.add('open');
		}
	}

	/**
	 * 关闭分类下拉菜单
	 */
	closeCategoryDropdown(dropdown) {
		dropdown.classList.remove('open');
	}

	/**
	 * 选择分类项
	 */
	selectCategoryItem(catType, value) {
		// 停止所有正在播放的音频
		this.examViewer.audioManager.stopAllAudio();

		if (value.startsWith('section-')) {
			const sectionIndex = parseInt(value.replace('section-', ''));
			if (sectionIndex >= 0 && sectionIndex < (this.examViewer.currentExam?.exam_info?.sections?.length || 0)) {
				this.examViewer.stateManager.updateNavigationState(sectionIndex, 0, catType);
			}
		}
	}

	/**
	 * 选择分类
	 */
	selectCategory(categoryId) {
		// 停止所有正在播放的音频
		this.examViewer.audioManager.stopAllAudio();

		this.examViewer.stateManager.updateNavigationState(0, 0, categoryId);
	}
}
// Export to global scope
window.CategoryNavigationManager = CategoryNavigationManager;
