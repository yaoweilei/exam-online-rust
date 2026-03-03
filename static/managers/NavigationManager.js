/*---------------------------------------------------------------------------------------------
 *  Copyright (c) 2025 Yaoweilei. All rights reserved.
 *
 *  This software is proprietary and confidential.
 *  Unauthorized copying, distribution, modification, or use of this software,
 *  via any medium, is strictly prohibited without prior written permission.
 *--------------------------------------------------------------------------------------------*/

/**
 * 导航管理器 - 统一处理题目导航逻辑
 * 从 main.js 提取
 * 支持章节内、跨章节、跨分类导航
 */
class NavigationManager {
	constructor(examViewer) {
		this.examViewer = examViewer;
		this.logger = Logger.getLogger('NavigationManager');
	}

	/**
	 * 计算下一个题目位置
	 * @param {string} direction - 方向 ('next' 或 'prev')
	 * @returns {Object|null} 新位置对象或null
	 */
	calculateNextPosition(direction) {
		const { currentExam, currentSectionIndex, currentQuestionIndex, currentCategory } = this.examViewer;

		this.logger.debug('calculateNextPosition called with:', {
			direction,
			currentSectionIndex,
			currentQuestionIndex,
			currentCategory
		});

		if (!currentExam || !currentCategory) {
			this.logger.debug('Missing exam or category');
			return null;
		}

		const currentCategoryData = this.examViewer.getCurrentCategory();

		this.logger.debug('currentCategoryData:', currentCategoryData);

		if (!currentCategoryData) {
			return null;
		}

		const sections = currentExam.exam_info?.sections || [];
		const currentSection = sections[currentSectionIndex];

		this.logger.info('Current section:', currentSection);

		if (direction === 'next') {
			return this.calculateNextQuestionPosition(currentCategoryData, sections, currentSection);
		} else if (direction === 'prev') {
			const result = this.calculatePrevQuestionPosition(currentCategoryData, sections, currentSection);
			console.log('[NavigationManager] Previous position result:', result);
			return result;
		}

		return null;
	}

	/**
	 * 计算下一题位置
	 */
	calculateNextQuestionPosition(currentCategoryData, sections, currentSection) {
		const { currentSectionIndex, currentQuestionIndex } = this.examViewer;

		// 检查当前章节是否还有下一题
		if (currentSection && Array.isArray(currentSection.questions) &&
			currentQuestionIndex < currentSection.questions.length - 1) {
			return {
				sectionIndex: currentSectionIndex,
				questionIndex: currentQuestionIndex + 1
			};
		}

		// 查找下一个章节
		const currentSectionIndexInCategory = currentCategoryData.sectionIndexes.indexOf(currentSectionIndex);
		if (currentSectionIndexInCategory < currentCategoryData.sectionIndexes.length - 1) {
			const nextSectionIndex = currentCategoryData.sectionIndexes[currentSectionIndexInCategory + 1];
			return {
				sectionIndex: nextSectionIndex,
				questionIndex: 0
			};
		}

		// 跨分类导航
		const categories = this.examViewer.getCategories();
		const currentCategoryIndex = categories.findIndex(cat => cat.id === this.examViewer.currentCategory);
		if (currentCategoryIndex < categories.length - 1) {
			const nextCategory = categories[currentCategoryIndex + 1];
			return {
				sectionIndex: nextCategory.sectionIndexes[0],
				questionIndex: 0,
				categoryId: nextCategory.id
			};
		}
	}

	/**
	 * 计算上一题位置
	 */
	calculatePrevQuestionPosition(currentCategoryData, sections, currentSection) {
		const { currentSectionIndex, currentQuestionIndex } = this.examViewer;

		// 检查当前章节是否还有上一题
		if (currentQuestionIndex > 0) {
			return {
				sectionIndex: currentSectionIndex,
				questionIndex: currentQuestionIndex - 1
			};
		}

		// 查找上一个章节
		const currentSectionIndexInCategory = currentCategoryData.sectionIndexes.indexOf(currentSectionIndex);

		this.logger.debug('calculatePrevQuestionPosition:', {
			currentSectionIndex,
			currentSectionIndexInCategory,
			sectionIndexes: currentCategoryData.sectionIndexes
		});

		if (currentSectionIndexInCategory > 0) {
			const prevSectionIndex = currentCategoryData.sectionIndexes[currentSectionIndexInCategory - 1];
			const prevSection = sections[prevSectionIndex];

			if (prevSection && Array.isArray(prevSection.questions) && prevSection.questions.length > 0) {
				const lastQuestionIndex = prevSection.questions.length - 1;
				return {
					sectionIndex: prevSectionIndex,
					questionIndex: lastQuestionIndex
				};
			} else {
				// 如果上一个章节没有题目，继续向前查找
				for (let i = currentSectionIndexInCategory - 2; i >= 0; i--) {
					const sectionIndex = currentCategoryData.sectionIndexes[i];
					const section = sections[sectionIndex];
					if (section && Array.isArray(section.questions) && section.questions.length > 0) {
						return {
							sectionIndex: sectionIndex,
							questionIndex: section.questions.length - 1
						};
					}
				}
			}
		}

		// 跨分类导航：查找上一个分类
		const categories = this.examViewer.getCategories();
		const currentCategoryIndex = categories.findIndex(cat => cat.id === this.examViewer.currentCategory);
		if (currentCategoryIndex > 0) {
			const prevCategory = categories[currentCategoryIndex - 1];
			if (prevCategory.sectionIndexes.length > 0) {
				const lastSectionIndex = prevCategory.sectionIndexes[prevCategory.sectionIndexes.length - 1];
				const lastSection = sections[lastSectionIndex];
				if (lastSection && Array.isArray(lastSection.questions) && lastSection.questions.length > 0) {
					const lastQuestionIndex = lastSection.questions.length - 1;
					return {
						sectionIndex: lastSectionIndex,
						questionIndex: lastQuestionIndex,
						categoryId: prevCategory.id
					};
				}
			}
		}

		this.logger.debug('Already at first question of entire exam');
		return null;
	}

	/**
	 * 导航到指定位置
	 * @param {string} direction - 方向 ('next' 或 'prev')
	 * @returns {boolean} 是否成功导航
	 */
	navigateToQuestion(direction) {
		this.logger.debug('========== navigateToQuestion START ==========');
		this.logger.debug('navigateToQuestion called with:', {
			direction,
			examExists: !!this.examViewer.currentExam,
			currentCategory: this.examViewer.currentCategory
		});

		const newPosition = this.calculateNextPosition(direction);

		this.logger.debug('newPosition:', newPosition);

		if (!newPosition) {
			this.logger.debug('No new position found');
			this.logger.debug('========== navigateToQuestion END (no position) ==========');
			return false;
		}

		this.logger.debug('Calling stateManager.updateNavigationState with:', {
			sectionIndex: newPosition.sectionIndex,
			questionIndex: newPosition.questionIndex,
			categoryId: newPosition.categoryId,
			stateManagerExists: !!this.examViewer.stateManager
		});

		try {
			this.examViewer.stateManager.updateNavigationState(
				newPosition.sectionIndex,
				newPosition.questionIndex,
				newPosition.categoryId
			);
			this.logger.info('Navigation completed successfully');
		} catch (error) {
			this.logger.error('State update error:', error);
			this.logger.debug('========== navigateToQuestion END (error) ==========');
			return false;
		}

		this.logger.debug('========== navigateToQuestion END (success) ==========');
		return true;
	}
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
	module.exports = NavigationManager;
}
// Export to global scope
window.NavigationManager = NavigationManager;
