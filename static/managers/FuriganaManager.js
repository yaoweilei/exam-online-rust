/*---------------------------------------------------------------------------------------------
 *  Copyright (c) 2025 Yaoweilei. All rights reserved.
 *
 *  This software is proprietary and confidential.
 *  Unauthorized copying, distribution, modification, or use of this software,
 *  via any medium, is strictly prohibited without prior written permission.
 *--------------------------------------------------------------------------------------------*/

/**
 * 振假名管理器 - 负责日语振假名标注
 * 
 * 注意：试卷数据的振假名标注已迁移到后端 (src/furigana_service.py)
 * 此管理器主要用于：
 * 1. 客户端实时标注（用户输入等场景）
 * 2. 调试和开发辅助
 * 
 * 优先使用后端预处理的数据，减少前端计算负担
 */
class FuriganaManager {
	constructor(examViewer) {
		this.examViewer = examViewer;
		this.furiganaDict = null;
		this._furiganaLoading = false;
		this._furiganaVersion = 0;
		this._furiganaRegex = null;
		this._furiganaMap = null;
		this._furiganaBadge = null;
		
		// 优先使用后端预处理的数据
		this.preferBackendProcessing = true;
	}

	/**
	 * 初始化振假名调试徽章
	 */
	initFuriganaDebugBadge() {
		try {
			if (!document.getElementById('furigana-debug-badge')) {
				const badge = document.createElement('div');
				badge.id = 'furigana-debug-badge';
				badge.textContent = 'Furigana: init';
				badge.style.cssText = 'position:fixed;z-index:9999;right:6px;bottom:6px;font:11px/1.2 monospace;padding:4px 6px;border-radius:4px;background:rgba(0,0,0,.55);color:#fff;cursor:pointer;user-select:none;max-width:42vw;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
				badge.title = '点击复制字典 URL / 双击隐藏';

				badge.addEventListener('click', (e) => {
					if (window.__FURIGANA_DICT_URL__) {
						navigator.clipboard?.writeText(window.__FURIGANA_DICT_URL__).catch(() => { });
						badge.textContent = 'URL 已复制';
						setTimeout(() => this.updateFuriganaStatus(), 1200);
					}
				});

				badge.addEventListener('dblclick', () => {
					badge.style.display = 'none';
				});

				document.addEventListener('keydown', (ev) => {
					if (ev.altKey && ev.key.toLowerCase() === 'f') {
						badge.style.display = 'block';
					}
				});

				document.body.appendChild(badge);
				this._furiganaBadge = badge;
				this.updateFuriganaStatus();
			}
		} catch (e) {
			console.warn('[FuriganaManager] Debug badge initialization failed:', e);
		}
	}

	/**
	 * 加载外部振假名字典
	 */
	loadExternalFuriganaDict() {
		if (this._furiganaLoading) return;
		const url = (window.__FURIGANA_DICT_URL__);
		if (!url) return;
		this._furiganaLoading = true;
		fetch(url).then(r => {
			if (!r.ok) throw new Error('HTTP ' + r.status);
			return r.json();
		}).then(json => {
			if (Array.isArray(json)) {
				this.furiganaDict = json;
				this._furiganaVersion++;
				const normalized = json.filter(d => d && d.w && d.r);
				normalized.sort((a, b) => b.w.length - a.w.length);
				this._furiganaMap = new Map(normalized.map(d => [d.w, d.r]));
				const escaped = normalized.map(d => d.w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
				this._furiganaRegex = escaped.length ? new RegExp('(' + escaped.join('|') + ')', 'g') : null;
				if (this.examViewer.showExplanations) {
					this.examViewer.questionRenderer.renderCurrentQuestion();
				}
				this.updateFuriganaStatus();
			}
		}).catch(err => console.warn('[FuriganaManager] Failed to load furigana dictionary', err));
	}

	/**
	 * 标注振假名
	 */
	annotateFurigana(text) {
		if (!text) return text;
		let dictSource = this.furiganaDict;
		if (!dictSource || !Array.isArray(dictSource) || dictSource.length === 0) {
			dictSource = [{ w: '絶叫', r: 'ぜっきょう' }, { w: '背後', r: 'はいご' }];
		}
		text = text.replace(/<ruby[^>]*data-auto-furi="1"[^>]*><rb>(.*?)<\/rb><rt>.*?<\/rt><\/ruby>/g, '$1');
		const manualRubyPlaceholders = [];
		text = text.replace(/<ruby(?![^>]*data-auto-furi)[^>]*>.*?<\/ruby>/g, m => {
			const idx = manualRubyPlaceholders.length;
			manualRubyPlaceholders.push(m);
			return `__RUBY_MANUAL_${idx}__`;
		});
		if (this._furiganaRegex && this._furiganaMap) {
			text = text.replace(this._furiganaRegex, m => {
				const kana = this._furiganaMap.get(m);
				return kana ? `<ruby data-auto-furi="1"><rb>${m}</rb><rt>${kana}</rt></ruby>` : m;
			});
		} else {
			const normalized = dictSource.filter(d => d && d.w && d.r);
			normalized.sort((a, b) => b.w.length - a.w.length);
			const escaped = normalized.map(d => d.w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
			if (escaped.length) {
				const re = new RegExp('(' + escaped.join('|') + ')', 'g');
				text = text.replace(re, (m) => {
					const entry = normalized.find(d => d.w === m);
					return entry ? `<ruby data-auto-furi="1"><rb>${m}</rb><rt>${entry.r}</rt></ruby>` : m;
				});
			}
		}
		text = text.replace(/__RUBY_MANUAL_(\d+)__/g, (_, i) => manualRubyPlaceholders[Number(i)] || '');
		return text;
	}

	/**
	 * 更新振假名状态
	 */
	updateFuriganaStatus() {
		const badge = this._furiganaBadge || document.getElementById('furigana-debug-badge');
		if (!badge) return;
		let label = 'Furigana: ';
		if (this._furiganaLoading && !this.furiganaDict) {
			label += 'loading…';
		} else if (this.furiganaDict && Array.isArray(this.furiganaDict) && this.furiganaDict.length) {
			label += 'ok ' + this.furiganaDict.length;
			if (this._furiganaVersion) label += ' v' + this._furiganaVersion;
		} else {
			label += 'fallback';
		}
		badge.textContent = label;
	}
}
// Export to global scope
window.FuriganaManager = FuriganaManager;
