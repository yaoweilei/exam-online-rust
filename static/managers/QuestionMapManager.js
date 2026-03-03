/*---------------------------------------------------------------------------------------------
 *  Copyright (c) 2025 Yaoweilei. All rights reserved.
 *
 *  This software is proprietary and confidential.
 *  Unauthorized copying, distribution, modification, or use of this software,
 *  via any medium, is strictly prohibited without prior written permission.
 *--------------------------------------------------------------------------------------------*/


class QuestionMapManager {
	constructor(examViewer) {
		this.examViewer = examViewer;
		this.questionMapVisible = false;
		this.questionMapContainer = null;
		this.questionMapContent = null;
	}

	/**
	 * 初始化答题卡
	 */
	initQuestionMap() {
		this.questionMapVisible = false;
		this.questionMapContainer = null;
	}

	/**
	 * 显示答题卡
	 */
	showQuestionMap() {
		if (!this.examViewer.currentExam) { return; }

		if (!this.questionMapContainer) {
			this.createQuestionMapOverlay();
		}

		this.questionMapVisible = true;
		this.questionMapContainer.style.display = 'flex';
		this.renderQuestionMap();
	}

	/**
	 * 隐藏答题卡
	 */
	hideQuestionMap() {
		if (this.questionMapContainer) {
			this.questionMapContainer.style.display = 'none';
		}
		this.questionMapVisible = false;
	}

	/**
	 * 创建答题卡覆盖层
	 */
	createQuestionMapOverlay() {
		this.questionMapContainer = document.createElement('div');
		this.questionMapContainer.id = 'question-map-overlay';
		this.questionMapContainer.style.cssText = `
			position: fixed;
			top: 0;
			left: 0;
			width: 100%;
			height: 100%;
			background: rgba(0, 0, 0, 0.5);
			z-index: 1000;
			display: flex;
			align-items: center;
			justify-content: center;
		`;
		document.body.appendChild(this.questionMapContainer);

		const mapContent = document.createElement('div');
		mapContent.style.cssText = `
			background: white;
			border-radius: 8px;
			padding: 12px;
			width: 350px;
			max-width: 90vw;
			max-height: 45vh;
			overflow-y: auto;
			box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
		`;

		const style = document.createElement('style');
		style.textContent = `
			#question-map-content { 
				margin-top: 6px;
				padding: 0 4px;
			}

			/* 分类容器 */
			.question-map-category {
				margin-bottom: 12px;
				border: 1px solid var(--vscode-panel-border, rgba(0,0,0,0.12));
				border-radius: 6px;
				padding: 8px;
				background: var(--vscode-input-background, rgba(0,0,0,0.02));
			}

			.question-map-category:last-child {
				margin-bottom: 0;
			}

			/* 分类标题 */
			.question-map-category-title {
				margin: 0 0 10px 0;
				font-size: 14px;
				font-weight: 700;
				color: var(--vscode-foreground, rgba(0,0,0,0.85));
				padding: 4px 8px;
				background: var(--vscode-button-background, rgba(0,122,204,0.08));
				border-radius: 4px;
				border-left: 3px solid var(--vscode-button-background, rgba(0,122,204,0.6));
			}

			/* Section 容器 */
			.question-map-section {
				display: flex;
				gap: 10px;
				margin-bottom: 8px;
				align-items: center;
			}

			.question-map-section:last-child {
				margin-bottom: 0;
			}

			/* Section 标签（問題X） */
			.question-map-section-label {
				font-size: 13px;
				font-weight: 600;
				color: var(--vscode-foreground, rgba(0,0,0,0.75));
				white-space: nowrap;
				text-align: left;
				padding: 0;
				min-width: 36px;
				width: 36px;
				flex-shrink: 0;
			}

			/* 题号容器（Grid布局，每行8个） */
			.question-map-section-questions {
				display: grid;
				grid-template-columns: repeat(8, 26px);
				gap: 5px;
				flex: 1;
			}

			/* 题号按钮 */
			.question-map-item {
				width: 26px;
				height: 26px;
				display: flex;
				align-items: center;
				justify-content: center;
				font-size: 10px;
				font-weight: 500;
				border-radius: 4px;
				border: 1px solid var(--vscode-panel-border, rgba(0,0,0,0.15));
				cursor: pointer;
				user-select: none;
				transition: all 0.2s ease;
				background: var(--vscode-editor-background, white);
				color: var(--vscode-foreground, black);
			}

			.question-map-item:hover {
				background: var(--vscode-list-hoverBackground, rgba(0,122,204,0.1));
				border-color: var(--vscode-button-background, rgba(0,122,204,0.4));
				transform: translateY(-2px);
				box-shadow: 0 2px 4px rgba(0,0,0,0.1);
			}

			.question-map-item.current {
				outline: 2px solid var(--vscode-button-background, rgba(0,122,204,0.9));
				background: var(--vscode-button-background, rgba(0,122,204,0.2));
				font-weight: 700;
				color: var(--vscode-button-foreground, white);
			}

			.question-map-item.correct {
				background: rgba(0, 200, 0, 0.12);
				border-color: var(--vscode-testing-iconPassed, rgba(0, 200, 0, 0.4));
				color: var(--vscode-testing-iconPassed, rgba(0, 150, 0, 1));
			}

			.question-map-item.incorrect {
				background: rgba(255, 0, 0, 0.1);
				border-color: var(--vscode-testing-iconFailed, rgba(255, 0, 0, 0.3));
				color: var(--vscode-testing-iconFailed, rgba(200, 0, 0, 1));
			}

			.question-map-item.unanswered {
				background: var(--vscode-editor-background, white);
				color: var(--vscode-foreground, black);
			}

			.question-map-item.answered {
				background: var(--vscode-button-background, rgba(0, 122, 204, 0.2));
				border-color: var(--vscode-button-background, rgba(0, 122, 204, 0.6));
				color: var(--vscode-button-foreground, white);
			}
		`;

		mapContent.appendChild(style);

		const closeBtn = document.createElement('button');
		closeBtn.setAttribute('aria-label', '关闭');
		closeBtn.innerHTML = '✕';
		closeBtn.style.cssText = `
			position: absolute;
			top: 6px;
			right: 6px;
			width: 20px;
			height: 20px;
			line-height: 18px;
			border-radius: 10px;
			border: none;
			background: rgba(0,0,0,0.05);
			font-size: 12px;
			cursor: pointer;
			color: rgba(0,0,0,0.6);
			transition: all 0.2s ease;
		`;
		closeBtn.onmouseover = () => {
			closeBtn.style.background = 'rgba(255,0,0,0.1)';
			closeBtn.style.color = 'rgba(255,0,0,0.8)';
		};
		closeBtn.onmouseout = () => {
			closeBtn.style.background = 'rgba(0,0,0,0.05)';
			closeBtn.style.color = 'rgba(0,0,0,0.6)';
		};
		closeBtn.onclick = (e) => { e.stopPropagation(); this.hideQuestionMap(); };

		mapContent.appendChild(closeBtn);

		const title = document.createElement('h3');
		title.textContent = '答题卡';
		title.style.marginTop = '0';
		mapContent.appendChild(title);

		this.questionMapContent = document.createElement('div');
		this.questionMapContent.id = 'question-map-content';
		mapContent.appendChild(this.questionMapContent);

		this.questionMapContainer.appendChild(mapContent);

		this.questionMapContainer.addEventListener('click', (e) => {
			if (e.target === this.questionMapContainer) {
				this.hideQuestionMap();
			}
		});
	}

	/**
	 * 渲染答题卡（按分类显示）
	 */
	renderQuestionMap() {
		if (!this.questionMapContent || !this.examViewer.currentExam) { 
			console.warn('[QuestionMapManager] Cannot render: missing content or exam');
			return; 
		}

		const sections = this.examViewer.currentExam.exam_info?.sections || [];
		const categories = this.examViewer.getCategories();
		
		console.log('[QuestionMapManager] Rendering question map:', {
			sectionsCount: sections.length,
			categoriesCount: categories.length,
			categories: categories.map(c => ({ id: c.id, label: c.label, sections: c.sectionIndexes.length }))
		});

		let html = '';

		// 按分类渲染
		categories.forEach(category => {
			if (category.sectionIndexes.length === 0) { 
				console.log(`[QuestionMapManager] Skipping empty category: ${category.label}`);
				return; 
			}

			// 分类标题
			html += `<div class="question-map-category">
				<h3 class="question-map-category-title">${category.label}</h3>`;

			// 遍历该分类下的所有 section
			category.sectionIndexes.forEach(sectionIndex => {
				const section = sections[sectionIndex];
				if (!section || !section.questions || section.questions.length === 0) { 
					console.log(`[QuestionMapManager] Skipping empty section at index ${sectionIndex}`);
					return; 
				}

				console.log(`[QuestionMapManager] Rendering section ${sectionIndex}: ${section.questions.length} questions`);

				// 提取"問題X"
				const sectionTitle = section.section_title || '';
				const match = sectionTitle.match(/問題\d+/);
				const sectionLabel = match ? match[0] : `Section ${section.section_id}`;

				html += `<div class="question-map-section">
					<span class="question-map-section-label">${sectionLabel}</span>
					<div class="question-map-section-questions">`;

				// 渲染题号
				section.questions.forEach((question, questionIndex) => {
					const questionId = `${sectionIndex}:${question.id || questionIndex}`;
					const isCurrent = sectionIndex === this.examViewer.currentSectionIndex && questionIndex === this.examViewer.currentQuestionIndex;
					
					// 检查是否已答题（使用复合键）
					let isAnswered = false;
					let userAnswer = undefined;
					
					try {
						userAnswer = this.examViewer.answerManager.getAnswerComposite(sectionIndex, question.id);
						isAnswered = userAnswer !== undefined && userAnswer !== null;
					} catch (e) {
						// 如果复合键方法失败，尝试直接访问
						isAnswered = this.examViewer.userAnswers[questionId] !== undefined && 
						             this.examViewer.userAnswers[questionId] !== null;
					}

					// 评估答案是否正确（仅在显示答案模式下）
					let isCorrect = false;
					if (isAnswered && this.examViewer.showAnswers) {
						try {
							isCorrect = this.examViewer.answerManager.evaluateQuestionAnswer(sectionIndex, questionIndex);
						} catch (e) {
							console.warn('[QuestionMapManager] Failed to evaluate answer:', e);
							isCorrect = false;
						}
					}

					// 确定状态类
					let statusClass = 'unanswered';
					if (isAnswered) {
						if (this.examViewer.showAnswers) {
							statusClass = isCorrect ? 'correct' : 'incorrect';
						} else {
							statusClass = 'answered';
						}
					}
					if (isCurrent) {
						statusClass += ' current';
					}

					html += `<span class="question-map-item ${statusClass}" data-section="${sectionIndex}" data-question="${questionIndex}">
						${questionIndex + 1}
					</span>`;
				});

				html += `</div></div>`;
			});

			html += `</div>`;
		});

		console.log('[QuestionMapManager] Generated HTML length:', html.length);
		this.questionMapContent.innerHTML = html;

		// 添加点击事件
		this.questionMapContent.addEventListener('click', (e) => {
			const target = e.target;
			const item = target.closest && target.closest('.question-map-item');
			if (item) {
				const sectionIndex = parseInt(item.getAttribute('data-section'));
				const questionIndex = parseInt(item.getAttribute('data-question'));
				this.selectQuestion(sectionIndex, questionIndex, true);
			}
		});
	}

	/**
	 * 选择题目
	 */
	selectQuestion(sectionIndex, questionIndex, keepOpen = false) {
		// 停止所有正在播放的音频
		this.examViewer.audioManager.stopAllAudio();

		this.examViewer.stateManager.updateNavigationState(sectionIndex, questionIndex);
		this.refreshQuestionMapHighlight();
		if (!keepOpen) {
			this.hideQuestionMap();
		}
	}

	/**
	 * 刷新答题卡高亮
	 */
	refreshQuestionMapHighlight() {
		if (!this.questionMapVisible || !this.questionMapContent) { return; }

		this.questionMapContent.querySelectorAll('.question-map-item').forEach(item => {
			item.classList.remove('current');
		});

		const currentItem = this.questionMapContent.querySelector(
			`.question-map-item[data-section="${this.examViewer.currentSectionIndex}"][data-question="${this.examViewer.currentQuestionIndex}"]`
		);
		if (currentItem) {
			currentItem.classList.add('current');
		}
	}

	/**
	 * 刷新答题状态
	 */
	refreshQuestionMapAnswered() {
		this.evaluateAnswersInMap();
	}

	/**
	 * 评估答题卡中的答案
	 */
	evaluateAnswersInMap() {
		if (!this.questionMapContent) { return; }

		const items = this.questionMapContent.querySelectorAll('.question-map-item');
		items.forEach(item => {
			const sectionIndex = parseInt(item.getAttribute('data-section'));
			const questionIndex = parseInt(item.getAttribute('data-question'));
			const isCorrect = this.examViewer.answerManager.evaluateQuestionAnswer(sectionIndex, questionIndex);

			item.classList.remove('correct', 'incorrect');
			if (this.examViewer.userAnswers[`${sectionIndex}:${questionIndex}`] !== undefined) {
				item.classList.add(isCorrect ? 'correct' : 'incorrect');
			}
		});
	}
}
// Export to global scope
window.QuestionMapManager = QuestionMapManager;
