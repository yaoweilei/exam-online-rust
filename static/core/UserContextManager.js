/*---------------------------------------------------------------------------------------------
 *  Copyright (c) 2025 Yaoweilei. All rights reserved.
 *
 *  This software is proprietary and confidential.
 *  Unauthorized copying, distribution, modification, or use of this software,
 *  via any medium, is strictly prohibited without prior written permission.
 *--------------------------------------------------------------------------------------------*/

/**
 * 用户上下文管理器（单例模式）
 * 从 main.js 提取
 */
class UserContextManager {
	static instance = null;

	/**
	 * 获取单例实例
	 * @returns {UserContextManager} 管理器实例
	 */
	static getInstance() {
		if (!this.instance) {
			this.instance = new UserContextManager();
		}
		return this.instance;
	}

	constructor() {
		this.userContext = { guest: true };
		this.listeners = new Set();
	}

	/**
	 * 设置用户上下文
	 * @param {Object} context - 用户上下文对象
	 */
	setUserContext(context) {
		this.userContext = { ...context };
		this.notifyChange();
	}

	/**
	 * 获取用户上下文
	 * @returns {Object} 用户上下文对象
	 */
	getUserContext() {
		return { ...this.userContext };
	}

	/**
	 * 通知上下文变更
	 */
	notifyChange() {
		// 触发全局事件
		window.dispatchEvent(new CustomEvent('userContextChanged', {
			detail: this.userContext
		}));

		// 通知VS Code后端
		try {
			if (typeof vscode !== 'undefined') {
				vscode.postMessage({ type: 'userContext', data: this.userContext });
			}
		} catch (error) {
			console.warn('[UserContextManager] Failed to notify backend:', error);
		}

		// 通知所有监听器
		this.listeners.forEach(listener => {
			try {
				listener(this.userContext);
			} catch (error) {
				console.warn('[UserContextManager] Listener error:', error);
			}
		});
	}

	/**
	 * 添加上下文变更监听器
	 * @param {Function} listener - 监听器函数
	 */
	addListener(listener) {
		this.listeners.add(listener);
	}

	/**
	 * 移除上下文变更监听器
	 * @param {Function} listener - 监听器函数
	 */
	removeListener(listener) {
		this.listeners.delete(listener);
	}
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
	module.exports = UserContextManager;
}
// Export to global scope
window.UserContextManager = UserContextManager;
