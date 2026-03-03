/*---------------------------------------------------------------------------------------------
 *  Copyright (c) 2025 Yaoweilei. All rights reserved.
 *
 *  This software is proprietary and confidential.
 *  Unauthorized copying, distribution, modification, or use of this software,
 *  via any medium, is strictly prohibited without prior written permission.
 *--------------------------------------------------------------------------------------------*/

/**
 * 音频管理器 - 负责音频播放和脚本同步
 */
class AudioManager {
	constructor(examViewer) {
		this.examViewer = examViewer;
		this.audioPlayers = new Map();
	}

	/**
	 * 创建音频播放器元素
	 */
	createAudioPlayerElement(question) {
		const audioDiv = document.createElement("div");
		audioDiv.className = "audio-player";
		audioDiv.dataset.questionId = question.id;

		const controlsDiv = document.createElement("div");
		controlsDiv.className = "audio-controls";

		const playBtn = document.createElement("button");
		playBtn.className = "audio-btn";
		playBtn.dataset.questionId = question.id;
		playBtn.dataset.playing = "false"; // 初始状态为未播放
		playBtn.addEventListener("click", () => this.togglePlayPause(question, playBtn));

		const progressDiv = document.createElement("div");
		progressDiv.className = "audio-progress";
		progressDiv.addEventListener("click", (e) => this.seekToProgress(e, question));
		// 添加拖动功能
		this.addProgressDragSupport(progressDiv, question);

		const progressBar = document.createElement("div");
		progressBar.className = "audio-progress-bar";
		progressBar.dataset.questionId = question.id;
		progressDiv.appendChild(progressBar);

		const timeDisplay = document.createElement("span");
		timeDisplay.className = "audio-time";
		timeDisplay.textContent = "0:00 / 0:00";
		timeDisplay.dataset.questionId = question.id;

		controlsDiv.appendChild(playBtn);
		controlsDiv.appendChild(progressDiv);
		controlsDiv.appendChild(timeDisplay);

		audioDiv.appendChild(controlsDiv);

		return audioDiv;
	}

	/**
	 * 创建脚本元素
	 */
	createScriptElement(question) {
		const scriptDiv = document.createElement("div");
		scriptDiv.className = "script-container";

		if (question.script && Array.isArray(question.script)) {
			question.script.forEach((line) => {
				const lineDiv = document.createElement("div");
				lineDiv.dataset.start = line.start;
				lineDiv.dataset.end = line.end;
				lineDiv.dataset.questionId = question.id;

				if (line.speaker) {
					// 检查文本是否已经包含speaker标识
					const speakerPattern = new RegExp(`^(${line.speaker})[：:]\\s*`);
					const match = line.text.match(speakerPattern);

					if (match) {
						// 文本中已包含speaker，只高亮speaker部分（不包括冒号）
						lineDiv.className = "script-line";

						const speakerSpan = document.createElement("span");
						speakerSpan.className = "speaker";
						speakerSpan.textContent = line.speaker; // 只显示"女"或"男"，不包括冒号
						lineDiv.appendChild(speakerSpan);

						const textSpan = document.createElement("span");
						textSpan.className = "script-text";
						// 移除speaker标识后的文本（包括冒号和空格）
						textSpan.textContent = line.text.substring(match[0].length);
						lineDiv.appendChild(textSpan);
					} else {
						// 文本中不包含speaker，添加到前面
						lineDiv.className = "script-line";

						const speakerSpan = document.createElement("span");
						speakerSpan.className = "speaker";
						speakerSpan.textContent = line.speaker;
						lineDiv.appendChild(speakerSpan);

						const textSpan = document.createElement("span");
						textSpan.className = "script-text";
						textSpan.textContent = line.text;
						lineDiv.appendChild(textSpan);
					}
				} else {
					// 没有 speaker：单列布局
					lineDiv.className = "script-line no-speaker";

					const textSpan = document.createElement("span");
					textSpan.className = "script-text";
					textSpan.textContent = line.text;
					lineDiv.appendChild(textSpan);
				}

				// 添加点击事件：跳转到该句子的时间点
				lineDiv.addEventListener('click', () => {
					this.seekToScriptLine(lineDiv, question.id);
				});

				scriptDiv.appendChild(lineDiv);
			});
		}

		return scriptDiv;
	}

	/**
	 * 切换播放/暂停
	 */
	togglePlayPause(question, playBtn) {
		let audio = this.audioPlayers.get(question.id);

		if (!audio) {
			// 第一次播放，创建音频播放器
			if (!question.audio) {
				return;
			}

			audio = new Audio(question.audio);
			this.audioPlayers.set(question.id, audio);

			// 添加时间更新监听器
			audio.addEventListener("timeupdate", () => {
				this.updateScriptHighlight(question.id, audio.currentTime);
				this.updateProgressBar(question.id, audio.currentTime, audio.duration);
			});

			// 添加播放结束监听器
			audio.addEventListener("ended", () => {
				playBtn.dataset.playing = "false";
				this.updateProgressBar(question.id, 0, audio.duration);
			});

			// 开始播放
			audio.play();
			playBtn.dataset.playing = "true";
		} else {
			// 切换播放/暂停状态
			if (audio.paused) {
				audio.play();
				playBtn.dataset.playing = "true";
			} else {
				audio.pause();
				playBtn.dataset.playing = "false";
			}
		}
	}

	/**
	 * 更新进度条
	 */
	updateProgressBar(questionId, currentTime, duration) {
		const progressBar = document.querySelector(`.audio-progress-bar[data-question-id="${questionId}"]`);
		const timeDisplay = document.querySelector(`.audio-time[data-question-id="${questionId}"]`);

		if (progressBar && duration > 0) {
			const percentage = (currentTime / duration) * 100;
			progressBar.style.width = `${percentage}%`;
		}

		if (timeDisplay) {
			const current = this.formatTime(currentTime);
			const total = this.formatTime(duration);
			timeDisplay.textContent = `${current} / ${total}`;
		}
	}

	/**
	 * 格式化时间显示
	 */
	formatTime(seconds) {
		if (isNaN(seconds)) { return "0:00"; }
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}

	/**
	 * 点击进度条跳转
	 */
	seekToProgress(event, question) {
		const audio = this.audioPlayers.get(question.id);
		if (!audio) { return; }

		const progressDiv = event.currentTarget;
		const rect = progressDiv.getBoundingClientRect();
		const clickX = event.clientX - rect.left;
		const percentage = clickX / rect.width;
		const newTime = percentage * audio.duration;

		audio.currentTime = newTime;
	}

	/**
	 * 更新脚本高亮
	 */
	updateScriptHighlight(questionId, currentTime) {
		// 查找所有属于该问题的脚本行
		const scriptLines = document.querySelectorAll(
			`.script-line[data-question-id="${questionId}"]`
		);

		let foundActive = false;

		scriptLines.forEach((line) => {
			const start = this.parseTimeToSeconds(line.dataset.start);
			const end = this.parseTimeToSeconds(line.dataset.end);

			if (currentTime >= start && currentTime < end && !foundActive) {
				// 只高亮第一个匹配的行
				if (!line.classList.contains("active")) {
					line.classList.add("active");
					// 自动滚动到当前行
					this.scrollScriptLineIntoView(line);
				}
				foundActive = true;
			} else {
				line.classList.remove("active");
			}
		});
	}

	/**
	 * 解析时间字符串为秒数
	 */
	parseTimeToSeconds(timeString) {
		if (!timeString) {
			return 0;
		}

		const parts = timeString.split(":").map((part) => parseFloat(part));
		if (parts.length === 3) {
			return parts[0] * 3600 + parts[1] * 60 + parts[2];
		} else if (parts.length === 2) {
			return parts[0] * 60 + parts[1];
		}
		return 0;
	}

	/**
	 * 清除活动脚本行
	 */
	clearActiveScriptLines(questionId) {
		let active = document.querySelectorAll(`.script-line[data-question-id="${questionId}"] .active`);
		if (!active.length) {
			active = document.querySelectorAll(`.script-line[data-question-id="${questionId}"]`);
		}
		active.forEach(l => l.classList.remove('active'));
	}

	/**
	 * 跳转到脚本行
	 */
	seekToScriptLine(lineDiv, questionId) {
		// 获取或创建音频播放器
		let audio = this.audioPlayers.get(Number(questionId));
		const playBtn = document.querySelector(`.audio-btn[data-question-id="${questionId}"]`);

		if (!audio) {
			// 如果音频播放器不存在，需要先找到对应的 question 对象
			const currentSection = this.examViewer.currentExam.exam_info.sections[this.examViewer.currentSectionIndex];
			const question = currentSection.questions.find(q => q.id === questionId);

			if (!question || !question.audio) {
				console.log('No audio found for question:', questionId);
				return;
			}

			// 创建音频播放器
			audio = new Audio(question.audio);
			this.audioPlayers.set(questionId, audio);

			// 添加时间更新监听器
			audio.addEventListener("timeupdate", () => {
				this.updateScriptHighlight(questionId, audio.currentTime);
				this.updateProgressBar(questionId, audio.currentTime, audio.duration);
			});

			// 添加播放结束监听器
			audio.addEventListener("ended", () => {
				if (playBtn) { playBtn.dataset.playing = "false"; }
				this.updateProgressBar(questionId, 0, audio.duration);
			});
		}

		const start = this.parseTimeToSeconds(lineDiv.dataset.start);

		// 先暂停音频，避免在跳转时触发 timeupdate
		const wasPlaying = !audio.paused;
		audio.pause();

		// 清除所有激活状态
		document.querySelectorAll(`.script-line[data-question-id="${questionId}"]`).forEach(el => {
			el.classList.remove('active');
		});

		// 设置当前行为激活状态
		lineDiv.classList.add('active');
		this.scrollScriptLineIntoView(lineDiv);

		// 跳转到指定时间
		audio.currentTime = start;

		// 恢复播放状态
		if (wasPlaying || audio.paused) {
			audio.play().catch(() => {
				console.log('Audio play failed');
			});
			// 更新播放按钮状态
			if (playBtn) { playBtn.dataset.playing = "true"; }
		}
	}

	/**
	 * 滚动脚本行到视图
	 */
	scrollScriptLineIntoView(lineEl) {
		if (!lineEl) { return; }
		try {
			lineEl.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
		} catch (_) {
			lineEl.scrollIntoView();
		}
	}

	/**
	 * 添加进度条拖动支持
	 */
	addProgressDragSupport(progressDiv, question) {
		let isDragging = false;

		// 鼠标按下
		progressDiv.addEventListener('mousedown', (e) => {
			isDragging = true;
			this.handleProgressDrag(e, progressDiv, question);
			e.preventDefault();
		});

		// 鼠标移动
		document.addEventListener('mousemove', (e) => {
			if (isDragging) {
				this.handleProgressDrag(e, progressDiv, question);
				e.preventDefault();
			}
		});

		// 鼠标释放
		document.addEventListener('mouseup', () => {
			isDragging = false;
		});

		// 触摸支持（移动设备）
		progressDiv.addEventListener('touchstart', (e) => {
			isDragging = true;
			this.handleProgressDrag(e.touches[0], progressDiv, question);
			e.preventDefault();
		});

		document.addEventListener('touchmove', (e) => {
			if (isDragging) {
				this.handleProgressDrag(e.touches[0], progressDiv, question);
				e.preventDefault();
			}
		});

		document.addEventListener('touchend', () => {
			isDragging = false;
		});
	}

	/**
	 * 处理进度条拖动
	 */
	handleProgressDrag(event, progressDiv, question) {
		const audio = this.audioPlayers.get(question.id);
		if (!audio || !audio.duration) { return; }

		const rect = progressDiv.getBoundingClientRect();
		const clickX = event.clientX - rect.left;
		const percentage = Math.max(0, Math.min(1, clickX / rect.width));
		const newTime = percentage * audio.duration;

		audio.currentTime = newTime;
		// 立即更新进度条显示
		this.updateProgressBar(question.id, newTime, audio.duration);
	}

	/**
	 * 跳转到指定时间
	 */
	jumpToAudioTime(timeString) {
		const audio = Array.from(this.audioPlayers.values())[0];
		if (audio) {
			const time = this.parseTimeToSeconds(timeString);
			audio.currentTime = time;
		}
	}

	/**
	 * 停止所有音频播放
	 */
	stopAllAudio() {
		this.audioPlayers.forEach((audio, questionId) => {
			// 停止播放
			audio.pause();
			audio.currentTime = 0;

			// 重置播放按钮状态
			const playBtn = document.querySelector(`.audio-btn[data-question-id="${questionId}"]`);
			if (playBtn) {
				playBtn.dataset.playing = "false";
			}

			// 重置进度条
			const progressBar = document.querySelector(`.audio-progress-bar[data-question-id="${questionId}"]`);
			if (progressBar) {
				progressBar.style.width = '0%';
			}

			// 重置时间显示
			const timeDisplay = document.querySelector(`.audio-time[data-question-id="${questionId}"]`);
			if (timeDisplay) {
				timeDisplay.textContent = '0:00 / 0:00';
			}
		});

		// 清除所有音频播放器实例
		this.audioPlayers.clear();

		// 清除所有高亮
		document.querySelectorAll('.script-line.active').forEach(el => {
			el.classList.remove('active');
		});
	}
}
// Export to global scope
window.AudioManager = AudioManager;
