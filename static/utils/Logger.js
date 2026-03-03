/**
 * 统一日志系统
 * 支持日志级别控制：DEBUG < INFO < WARN < ERROR
 */

class Logger {
	// 日志级别定义
	static LEVELS = {
		DEBUG: 0,
		INFO: 1,
		WARN: 2,
		ERROR: 3
	};

	// 日志级别名称映射
	static LEVEL_NAMES = ['DEBUG', 'INFO', 'WARN', 'ERROR'];

	// 日志级别颜色
	static LEVEL_COLORS = {
		DEBUG: '#999',      // 灰色
		INFO: '#2196F3',    // 蓝色
		WARN: '#FF9800',    // 橙色
		ERROR: '#F44336'    // 红色
	};

	// 当前日志级别（从配置或环境变量读取）
	static currentLevel = Logger.LEVELS.INFO;  // 默认 INFO

	/**
	 * 初始化日志系统
	 * @param {string} level - 日志级别：'DEBUG', 'INFO', 'WARN', 'ERROR'
	 */
	static init(level = 'INFO') {
		const upperLevel = level.toUpperCase();
		if (Logger.LEVELS.hasOwnProperty(upperLevel)) {
			Logger.currentLevel = Logger.LEVELS[upperLevel];
			console.log(`[Logger] 日志级别设置为: ${upperLevel}`);
		} else {
			console.warn(`[Logger] 无效的日志级别: ${level}，使用默认级别 INFO`);
		}
	}

	/**
	 * 从全局配置读取日志级别
	 */
	static initFromConfig() {
		const level = window.__LOG_LEVEL__ || 'INFO';
		Logger.init(level);
	}

	/**
	 * 检查是否应该输出日志
	 * @param {number} level - 日志级别
	 * @returns {boolean}
	 */
	static shouldLog(level) {
		return level >= Logger.currentLevel;
	}

	/**
	 * 格式化日志消息
	 * @param {string} tag - 标签
	 * @param {string} levelName - 级别名称
	 * @param {Array} args - 参数
	 * @returns {Array}
	 */
	static formatMessage(tag, levelName, args) {
		const timestamp = new Date().toLocaleTimeString();
		const prefix = `[${timestamp}] [${levelName}] [${tag}]`;
		return [prefix, ...args];
	}

	/**
	 * 创建日志记录器
	 * @param {string} tag - 标签（如 'ExamViewer', 'APIClient'）
	 * @returns {Object} 日志记录器对象
	 */
	static getLogger(tag) {
		return {
			/**
			 * DEBUG 级别日志
			 */
			debug: (...args) => {
				if (Logger.shouldLog(Logger.LEVELS.DEBUG)) {
					const msg = Logger.formatMessage(tag, 'DEBUG', args);
					console.log(...msg);
				}
			},

			/**
			 * INFO 级别日志
			 */
			info: (...args) => {
				if (Logger.shouldLog(Logger.LEVELS.INFO)) {
					const msg = Logger.formatMessage(tag, 'INFO', args);
					console.log(...msg);
				}
			},

			/**
			 * WARN 级别日志
			 */
			warn: (...args) => {
				if (Logger.shouldLog(Logger.LEVELS.WARN)) {
					const msg = Logger.formatMessage(tag, 'WARN', args);
					console.warn(...msg);
				}
			},

			/**
			 * ERROR 级别日志
			 */
			error: (...args) => {
				if (Logger.shouldLog(Logger.LEVELS.ERROR)) {
					const msg = Logger.formatMessage(tag, 'ERROR', args);
					console.error(...msg);
				}
			},

			/**
			 * 带样式的日志（用于重要信息）
			 */
			styled: (level, ...args) => {
				const levelNum = Logger.LEVELS[level.toUpperCase()];
				if (Logger.shouldLog(levelNum)) {
					const color = Logger.LEVEL_COLORS[level.toUpperCase()];
					const timestamp = new Date().toLocaleTimeString();
					console.log(
						`%c[${timestamp}] [${level}] [${tag}]`,
						`color: ${color}; font-weight: bold;`,
						...args
					);
				}
			}
		};
	}

	/**
	 * 设置日志级别
	 * @param {string} level - 日志级别
	 */
	static setLevel(level) {
		Logger.init(level);
	}

	/**
	 * 获取当前日志级别名称
	 * @returns {string}
	 */
	static getCurrentLevel() {
		return Logger.LEVEL_NAMES[Logger.currentLevel];
	}
}

// 导出到全局作用域
window.Logger = Logger;

// 自动从配置初始化
if (document.readyState === 'loading') {
	document.addEventListener('DOMContentLoaded', () => Logger.initFromConfig());
} else {
	Logger.initFromConfig();
}
