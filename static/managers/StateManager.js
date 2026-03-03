/*---------------------------------------------------------------------------------------------
 *  Copyright (c) 2025 Yaoweilei. All rights reserved.
 *
 *  This software is proprietary and confidential.
 *  Unauthorized copying, distribution, modification, or use of this software,
 *  via any medium, is strictly prohibited without prior written permission.
 *--------------------------------------------------------------------------------------------*/

/**
 * 状态管理器 - 统一管理ExamViewer状态
 * 从 main.js 提取
 */
class StateManager {
	constructor(examViewer) {
		this.examViewer = examViewer;
		this.logger = Logger.getLogger('StateManager');
	}

	/**
	 * 更新导航状态
	 * @param {number} sectionIndex - 章节索引
	 * @param {number} questionIndex - 题目索引
	 * @param {string} categoryId - 分类ID（可选）
	 */
	updateNavigationState(sectionIndex, questionIndex, categoryId = null) {
		this.logger.debug('updateNavigationState called:', {
			sectionIndex,
			questionIndex,
			categoryId,
			currentCategoryBefore: this.examViewer.currentCategory
		});

		this.examViewer.currentSectionIndex = sectionIndex;
		this.examViewer.currentQuestionIndex = questionIndex;

		if (categoryId && categoryId !== this.examViewer.currentCategory) {
			this.logger.info('Updating category:', {
				from: this.examViewer.currentCategory,
				to: categoryId
			});
			this.examViewer.currentCategory = categoryId;
		}

		this.logger.debug('currentCategory after:', this.examViewer.currentCategory);
		this.refreshUI();
	}

	/**
	 * 重置试卷状态
	 */
	resetExamState() {
		Object.assign(this.examViewer, {
			currentSectionIndex: 0,
			currentQuestionIndex: 0,
			userAnswers: {},
			showAnswers: false,
			showExplanations: false
		});
	}

	/**
	 * 刷新UI
	 */
	refreshUI() {
		// 使用 QuestionRenderer 渲染当前题目
		if (this.examViewer.questionRenderer) {
			this.examViewer.questionRenderer.renderCurrentQuestion();
		}
		// 渲染题目导航
		this.examViewer.renderQuestionNavigation();
	}

	/**
	 * 批量更新状态
	 * @param {Object} updates - 状态更新对象
	 */
	batchUpdate(updates) {
		Object.assign(this.examViewer, updates);
		this.refreshUI();
	}
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
	module.exports = StateManager;
}
// Export to global scope
window.StateManager = StateManager;
