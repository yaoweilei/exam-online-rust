/*---------------------------------------------------------------------------------------------
 *  Copyright (c) 2025 Yaoweilei. All rights reserved.
 *
 *  This software is proprietary and confidential.
 *  Unauthorized copying, distribution, modification, or use of this software,
 *  via any medium, is strictly prohibited without prior written permission.
 *--------------------------------------------------------------------------------------------*/

/**
 * DOM操作工具类
 * 从 main.js 提取
 */
class DOMUtils {
	/**
	 * 安全获取DOM元素
	 * @param {string} id - 元素ID
	 * @param {string} context - 上下文描述
	 * @returns {HTMLElement|null} DOM元素或null
	 */
	static safeGetElement(id, context = null) {
		const element = document.getElementById(id);
		if (!element && context) {
			console.warn(`[DOMUtils] Element not found: ${id} in context:`, context);
		}
		return element;
	}

	/**
	 * 创建带类名的元素
	 * @param {string} tag - 标签名
	 * @param {string} className - 类名
	 * @param {string} textContent - 文本内容
	 * @returns {HTMLElement} 创建的元素
	 */
	static createElementWithClass(tag, className, textContent = '') {
		const element = document.createElement(tag);
		if (className) { element.className = className; }
		if (textContent) { element.textContent = textContent; }
		return element;
	}

	/**
	 * 安全设置innerHTML
	 * @param {HTMLElement} element - 目标元素
	 * @param {string} html - HTML内容
	 * @param {string} context - 上下文描述
	 */
	static safeSetInnerHTML(element, html, context = '') {
		if (!element) {
			console.warn(`[DOMUtils] Cannot set innerHTML: element is null in context: ${context}`);
			return;
		}
		try {
			element.innerHTML = html;
		} catch (error) {
			if (typeof ErrorHandler !== 'undefined') {
				ErrorHandler.handle(error, 'DOMUtils', `设置HTML内容 (${context})`);
			} else {
				console.error('[DOMUtils] Error setting innerHTML:', error);
			}
		}
	}
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
	module.exports = DOMUtils;
}
// Export to global scope
window.DOMUtils = DOMUtils;
