/*---------------------------------------------------------------------------------------------
 *  Copyright (c) 2025 Yaoweilei. All rights reserved.
 *
 *  This software is proprietary and confidential.
 *  Unauthorized copying, distribution, modification, or use of this software,
 *  via any medium, is strictly prohibited without prior written permission.
 *--------------------------------------------------------------------------------------------*/

/**
 * DOM 辅助工具 - 统一处理 DOM 操作、事件和渲染
 * 合并了 EventManager 和 RenderManager
 */
class DOMHelpers {
	// ==================== 事件管理 ====================
	
	/**
	 * 批量添加事件监听器
	 * @param {HTMLElement} element - 目标元素
	 * @param {Object} events - 事件映射对象 {eventType: handler}
	 */
	static addEventListeners(element, events) {
		if (!element) return;
		Object.entries(events).forEach(([eventType, handler]) => {
			element.addEventListener(eventType, handler);
		});
	}

	/**
	 * 创建带事件的元素
	 * @param {Object} options - 配置选项
	 * @returns {HTMLElement} 创建的元素
	 */
	static createElement({ tag, className, textContent, events = {}, attributes = {} }) {
		const element = document.createElement(tag);
		if (className) element.className = className;
		if (textContent) element.textContent = textContent;

		// 设置属性
		Object.entries(attributes).forEach(([key, value]) => {
			element.setAttribute(key, value);
		});

		// 添加事件监听器
		this.addEventListeners(element, events);

		return element;
	}

	/**
	 * 事件委托 - 在父元素上监听子元素事件
	 * @param {HTMLElement} parent - 父元素
	 * @param {string} selector - 子元素选择器
	 * @param {string} eventType - 事件类型
	 * @param {Function} handler - 事件处理器
	 */
	static delegate(parent, selector, eventType, handler) {
		if (!parent) return;
		parent.addEventListener(eventType, (e) => {
			const target = e.target.closest(selector);
			if (target) {
				handler.call(target, e);
			}
		});
	}

	// ==================== 渲染管理 ====================
	
	/**
	 * 安全渲染到容器
	 * @param {string} containerId - 容器ID
	 * @param {Function} renderFunction - 渲染函数
	 * @param {string} context - 上下文描述
	 */
	static safeRender(containerId, renderFunction, context) {
		const container = document.getElementById(containerId);
		if (!container) {
			console.warn(`[DOMHelpers] Container not found: ${containerId} in ${context}`);
			return null;
		}

		try {
			return renderFunction(container);
		} catch (error) {
			console.error(`[DOMHelpers] Render failed in ${context}:`, error);
			return null;
		}
	}

	/**
	 * 批量设置元素属性
	 * @param {HTMLElement} element - 目标元素
	 * @param {Object} attributes - 属性对象
	 */
	static setAttributes(element, attributes) {
		if (!element) return;
		Object.entries(attributes).forEach(([key, value]) => {
			if (key === 'textContent') {
				element.textContent = value;
			} else if (key === 'innerHTML') {
				element.innerHTML = value;
			} else if (key === 'className') {
				element.className = value;
			} else {
				element.setAttribute(key, value);
			}
		});
	}
}

// 导出到全局作用域
window.DOMHelpers = DOMHelpers;

// 向后兼容
window.EventManager = DOMHelpers;
window.RenderManager = DOMHelpers;
