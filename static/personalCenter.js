/*---------------------------------------------------------------------------------------------
 *  Copyright (c) 2025 Yaoweilei. All rights reserved.
 *
 *  This software is proprietary and confidential.
 *  Unauthorized copying, distribution, modification, or use of this software,
 *  via any medium, is strictly prohibited without prior written permission.
 *--------------------------------------------------------------------------------------------*/


// personalCenter.js - 个人中心模块：与 main.js 解耦，负责用户状态、权限 gating、抽屉 UI
// Phase 1: 仅提供基础骨架 + 假数据；与 main.js 通过 window 共享事件

(function () { // 立即执行函数表达式(IIFE)，创建独立作用域避免全局变量污染
	const DEBUG = false; // 调试模式开关，控制是否输出调试信息
	const log = (...args) => { if (DEBUG) { console.log('[PC]', ...args); } }; // 条件调试日志函数，只在DEBUG为true时输出

	const readyState = document.readyState; // 获取当前文档的加载状态
	if (readyState === 'complete' || readyState === 'interactive') { // 检查文档是否已完全加载或可交互
		setTimeout(() => safeBuildTrigger('immediate-ready'), 0); // 使用setTimeout异步执行，确保在下一个事件循环中构建触发器
	} else { // 如果文档还在加载中
		document.addEventListener('DOMContentLoaded', () => safeBuildTrigger('domcontentloaded')); // 监听DOM加载完成事件，然后构建触发器
	}

	// ==================== 数据管理器 ====================
	// 个人中心数据管理器类，负责用户数据的加载、存储和管理
	class PersonalCenterDataManager {
		constructor() { // 构造函数，初始化数据管理器的基本属性
			this.allUsers = []; // 存储所有用户数据的数组
			this.userContextManager = null; // 用户上下文管理器的引用，初始为null
			this._userContext = { guest: true }; // 内部用户上下文，默认为访客状态
		}

		async loadAllUsers() {
			// 改为从后端 API 加载所有用户（仅超级管理员可见）
			if (this.allUsers.length > 0) { return this.allUsers; }

			try {
				// 获取所有角色的用户
				const roles = ['guest', 'student', 'teacher', 'reviewer', 'academicAdmin', 'systemAdmin', 'superAdmin'];
				const allUsersMap = new Map();
				
				for (const role of roles) {
					try {
						const users = await APIClient.getUsersByRole(role);
						users.forEach(u => allUsersMap.set(u.id, u));
					} catch (e) {
						log('Error loading users for role:', role, e);
					}
				}
				
				this.allUsers = Array.from(allUsersMap.values());
				log('Loaded users from API:', this.allUsers.length);
			} catch (e) {
				log('Error loading users:', e);
				this.allUsers = [];
			}
			return this.allUsers;
		}

		async getUsersByRole(roleId) {
			// 改为调用后端 API
			try {
				return await APIClient.getUsersByRole(roleId);
			} catch (e) {
				log('Error getting users by role:', e);
				return [];
			}
		}

		async saveAllUsers() {
			// 用户数据由后端管理，前端不再直接保存
			log('saveAllUsers: 用户数据由后端管理');
		}

		getUserContextManager() { // 获取用户上下文管理器实例
			if (!this.userContextManager && window.UserContextManager) { // 如果本地管理器不存在但全局管理器类存在
				this.userContextManager = window.UserContextManager.getInstance(); // 获取全局用户上下文管理器的单例实例
			}
			return this.userContextManager; // 返回用户上下文管理器实例
		}

		getCurrentUserContext() { // 获取当前用户上下文信息
			const manager = this.getUserContextManager(); // 获取用户上下文管理器
			if (manager) { // 如果管理器存在
				return manager.getUserContext(); // 使用管理器获取用户上下文
			}
			return this._userContext; // 否则返回本地存储的用户上下文
		}

		setUserContext(ctx) { // 设置用户上下文信息
			const manager = this.getUserContextManager(); // 获取用户上下文管理器
			const newContext = { ...ctx, guest: false }; // 创建新的用户上下文，确保guest属性为false

			if (manager) { // 如果管理器存在
				manager.setUserContext(newContext); // 使用管理器设置用户上下文
			} else { // 如果管理器不存在，使用本地方式
				this._userContext = newContext; // 更新本地用户上下文
				window.dispatchEvent(new CustomEvent('userContextChanged', { detail: newContext })); // 派发用户上下文变更事件
			}
		}

		logoutUser() { // 用户登出方法
			const manager = this.getUserContextManager(); // 获取用户上下文管理器
			const guestContext = { guest: true }; // 创建访客上下文对象

			if (manager) { // 如果管理器存在
				manager.setUserContext(guestContext); // 使用管理器设置为访客状态
			} else { // 如果管理器不存在，使用本地方式
				this._userContext = guestContext; // 更新本地用户上下文为访客状态
				window.dispatchEvent(new CustomEvent('userContextChanged', { detail: guestContext })); // 派发用户上下文变更事件
			}
		}
	}

	const dataManager = new PersonalCenterDataManager(); // 创建数据管理器实例，用于管理个人中心的所有数据操作

	// ==================== DOM工具类 ====================
	// DOM操作工具类，提供统一的DOM元素操作方法
	class PersonalCenterDOMUtils {
		static getElement(id, context = document) { // 安全获取DOM元素的静态方法
			const element = context.getElementById ? context.getElementById(id) : context.querySelector(`#${id}`); // 优先使用getElementById，回退到querySelector
			if (!element) { // 如果元素不存在
				log(`Element not found: #${id}`); // 记录元素未找到的警告信息
			}
			return element; // 返回找到的元素或null
		}

		static createElement(tag, className = '', innerHTML = '') { // 创建DOM元素的静态方法
			const element = document.createElement(tag); // 创建指定标签的DOM元素
			if (className) { element.className = className; } // 如果提供了类名，设置元素的className属性
			if (innerHTML) { element.innerHTML = innerHTML; } // 如果提供了HTML内容，设置元素的innerHTML属性
			return element; // 返回创建的DOM元素
		}

		static addEventListeners(element, events) { // 批量添加事件监听器的静态方法
			if (!element) { return; } // 如果元素不存在，直接返回
			Object.entries(events).forEach(([event, handler]) => { // 遍历事件对象的每个键值对
				element.addEventListener(event, handler, false); // 为元素添加事件监听器，第三个参数false表示在冒泡阶段处理
			});
		}

		static toggleClass(element, className, condition) { // 根据条件切换CSS类的静态方法
			if (!element) { return; } // 如果元素不存在，直接返回
			element.classList.toggle(className, condition); // 使用classList.toggle方法根据条件添加或移除CSS类
		}
	}

	// ==================== 用户上下文访问器 ====================
	// 使用Proxy创建用户上下文访问器，提供透明的属性访问
	const userContext = new Proxy({}, { // 创建一个空对象的代理
		get(target, prop) { // 定义属性访问的拦截器
			const context = dataManager.getCurrentUserContext(); // 从数据管理器获取当前用户上下文
			return context[prop]; // 返回用户上下文中对应属性的值
		}
	});

	window.setUserContext = (ctx) => { // 全局设置用户上下文的方法，暴露给外部调用
		dataManager.setUserContext(ctx); // 使用数据管理器设置用户上下文
		buildOrUpdateTrigger(); // 更新触发器按钮的显示状态
		if (isOpen()) { // 如果个人中心面板当前是打开状态
			renderSectionsNav(); // 重新渲染导航菜单
			renderActiveSection(); // 重新渲染当前活动的内容区域
		}
	};

	window.logoutUser = () => { // 全局用户登出方法，暴露给外部调用
		dataManager.logoutUser(); // 使用数据管理器执行登出操作
		closePanel(); // 关闭个人中心面板
		buildOrUpdateTrigger(); // 更新触发器按钮的显示状态
	};

	// ==================== 模板管理器 ====================
	// 模板管理器类，负责管理个人中心面板的HTML模板
	class TemplateManager {
		static getDefaultTemplate() { // 获取默认HTML模板的静态方法
			return ` // 返回个人中心面板的默认HTML结构
				<div class="pc-overlay" data-action="pc-close"></div> <!-- 遮罩层，点击可关闭面板 -->
				<aside class="pc-panel" role="dialog" aria-modal="true" aria-label="个人中心"> <!-- 主面板，设置为模态对话框 -->
					<header class="pc-header"> <!-- 面板头部区域 -->
						<div class="pc-user-inline"> <!-- 用户信息内联显示区域 -->
							<div class="pc-avatar" id="pc-avatar"></div> <!-- 用户头像容器 -->
							<div class="pc-user-meta"> <!-- 用户元信息容器 -->
								<div class="pc-name" id="pc-name"></div> <!-- 用户名显示区域 -->
								<div class="pc-roles" id="pc-roles"></div> <!-- 用户角色显示区域 -->
							</div>
						</div>
						<button class="pc-close" data-action="pc-close" aria-label="关闭">×</button> <!-- 关闭按钮 -->
					</header>
					<nav class="pc-nav" id="pc-nav"></nav> <!-- 导航菜单区域 -->
					<main class="pc-content" id="pc-content" tabindex="0"></main> <!-- 主内容区域，设置tabindex使其可获得焦点 -->
					<footer class="pc-footer">Exam Viewer · Personal Center</footer> <!-- 页脚信息 -->
				</aside>`;
		}

		static async loadTemplate() { // 异步加载模板的静态方法
			const templateScript = PersonalCenterDOMUtils.getElement('personal-center-template'); // 尝试获取模板脚本元素
			if (!templateScript) { // 如果模板脚本元素不存在
				return this.getDefaultTemplate(); // 返回默认模板
			}

			const src = templateScript.getAttribute('data-src') || templateScript.getAttribute('src'); // 获取模板的外部源地址
			if (src) { // 如果存在外部源地址
				try { // 尝试从外部源加载模板
					const response = await fetch(src); // 发起HTTP请求获取模板内容
					return await response.text(); // 返回响应的文本内容
				} catch (e) { // 如果加载失败
					log('Failed to load template from src:', e); // 记录加载失败的错误信息
					return templateScript.textContent || templateScript.innerHTML || this.getDefaultTemplate(); // 回退到脚本内容或默认模板
				}
			}

			return templateScript.textContent || templateScript.innerHTML || this.getDefaultTemplate(); // 返回脚本的文本内容或默认模板
		}
	}

	function ensureRoot() { // 确保个人中心根容器存在的函数
		let root = PersonalCenterDOMUtils.getElement('personal-center'); // 尝试获取已存在的个人中心根元素
		if (!root) { // 如果根元素不存在
			root = PersonalCenterDOMUtils.createElement('div', 'pc-hidden'); // 创建一个新的div元素，初始状态为隐藏
			root.id = 'personal-center'; // 设置元素的ID为'personal-center'

			// 异步加载模板但立即返回容器，避免阻塞主线程
			TemplateManager.loadTemplate().then(html => { // 异步加载HTML模板
				root.innerHTML = html; // 将加载的HTML内容设置到根元素中
			});

			document.body.appendChild(root); // 将根元素添加到页面body中
			PersonalCenterDOMUtils.addEventListeners(root, { // 为根元素添加点击事件监听器
				'click': onRootClick // 绑定根元素点击处理函数
			});
			PersonalCenterDOMUtils.addEventListeners(document, { // 为整个文档添加键盘事件监听器
				'keydown': onGlobalKey // 绑定全局键盘按键处理函数
			});
		}
		return root; // 返回个人中心根元素
	}

	// ==================== 触发器管理器 ====================
	// 触发器管理器类，负责管理个人中心入口按钮的创建和更新
	class TriggerManager {
		static async buildOrUpdate() { // 异步构建或更新触发器按钮的静态方法
			let trigger = PersonalCenterDOMUtils.getElement('user-menu-trigger'); // 尝试获取已存在的用户菜单触发器元素

			if (!trigger) { // 如果触发器元素不存在
				trigger = PersonalCenterDOMUtils.createElement('div', 'pc-trigger'); // 创建一个新的div元素作为触发器
				trigger.id = 'user-menu-trigger'; // 设置触发器元素的ID

				const workarea = PersonalCenterDOMUtils.getElement('exam-workarea') || document.body; // 获取工作区域元素，如果不存在则使用body
				if (!workarea) { // 如果工作区域也不存在
					console.warn('[personalCenter] #exam-workarea not found, using body as container'); // 输出警告信息
				}
				workarea.appendChild(trigger); // 将触发器元素添加到工作区域中

				PersonalCenterDOMUtils.addEventListeners(trigger, { // 为触发器添加点击事件监听器
					'click': () => { // 定义点击事件处理函数
						if (userContext.guest) { // 如果当前用户是访客状态
							openWeChatLogin(); // 打开微信登录界面
						} else { // 如果用户已登录
							openPanel(); // 打开个人中心面板
						}
					}
				});
			}

			this.updateTriggerContent(trigger); // 更新触发器按钮的显示内容
			await dataManager.loadAllUsers(); // 异步加载所有用户数据
		}

		static updateTriggerContent(trigger) { // 更新触发器内容的静态方法
			if (userContext.guest) { // 如果当前用户是访客状态
				trigger.textContent = '登录'; // 设置按钮文本为"登录"
				trigger.title = '登录账号'; // 设置按钮的提示文本
			} else { // 如果用户已登录
				trigger.textContent = initials(userContext.displayName || 'U'); // 设置按钮文本为用户名首字母
				trigger.title = (userContext.displayName || '') + ' - 打开个人中心'; // 设置按钮的提示文本包含用户名
			}
		}
	}

	async function buildOrUpdateTrigger() { // 异步构建或更新触发器的包装函数
		await TriggerManager.buildOrUpdate(); // 调用触发器管理器的构建或更新方法
	}

	function safeBuildTrigger(tag) { // 安全构建触发器的函数，包含错误处理和重试机制
		try { buildOrUpdateTrigger(); } catch (e) { console.error('[personalCenter] Trigger build failed', tag, e); } // 尝试构建触发器，如果失败则记录错误
		if (!document.getElementById('user-menu-trigger')) { // 如果触发器元素仍然不存在
			setTimeout(() => { // 设置延时重试机制
				if (!document.getElementById('user-menu-trigger')) { buildOrUpdateTrigger(); } // 500毫秒后再次尝试构建触发器
			}, 500); // 延时500毫秒
		}
	}



	function openPanel() { // 打开个人中心面板的函数
		const root = ensureRoot(); // 确保根容器存在并获取引用
		root.classList.remove('pc-hidden'); // 移除隐藏状态的CSS类
		root.classList.add('pc-open'); // 添加打开状态的CSS类
		renderIdentity(); // 渲染用户身份信息
		renderSectionsNav(); // 渲染导航菜单
		renderActiveSection(); // 渲染当前活动的内容区域
	}
	function closePanel() { // 关闭个人中心面板的函数
		const root = document.getElementById('personal-center'); // 获取个人中心根元素
		root.classList.remove('pc-open'); // 移除打开状态的CSS类
		root.classList.add('pc-hidden'); // 添加隐藏状态的CSS类
	}
	function isOpen() { // 检查个人中心面板是否处于打开状态的函数
		const root = document.getElementById('personal-center'); // 获取个人中心根元素
		return !!root && root.classList.contains('pc-open'); // 返回布尔值，表示元素存在且包含打开状态的CSS类
	}

	function onRootClick(e) { // 根元素点击事件处理函数
		const t = e.target; // 获取点击事件的目标元素
		if (t instanceof HTMLElement && t.dataset.action === 'pc-close') { // 如果目标是HTML元素且具有关闭动作的数据属性
			closePanel(); // 关闭个人中心面板
		}
	}
	function onGlobalKey(e) { // 全局键盘事件处理函数
		if (e.key === 'Escape' && isOpen()) { closePanel(); } // 如果按下Escape键且面板处于打开状态，则关闭面板
	}

	const sections = [ // 个人中心导航菜单配置数组，定义各个功能模块
		{ id: 'dashboard', title: '概览', gate: u => !u.guest }, // 概览页面，仅登录用户可见
		{ id: 'profile', title: '个人资料', gate: u => !u.guest }, // 个人资料页面，仅登录用户可见
		{ id: 'roles', title: '角色权限', gate: u => !u.guest }, // 角色权限页面，仅登录用户可见
		{ id: 'community', title: '社群', gate: u => !u.guest }, // 社群页面，仅登录用户可见
		{ id: 'balance', title: '账户', gate: u => !u.guest && hasAnyRole(u, ['student', 'teacher', 'reviewer', 'academicAdmin', 'systemAdmin', 'superAdmin']) }, // 账户页面，需要登录且具有特定角色
		{ id: 'admin-hub', title: '管理面板', gate: u => hasAnyRole(u, ['teacher', 'reviewer', 'academicAdmin', 'systemAdmin', 'superAdmin']) }, // 管理面板，仅管理员角色可见
		{ id: 'logout', title: '退出登录', gate: u => !u.guest } // 退出登录选项，仅登录用户可见
	];

	let activeSection = 'dashboard'; // 当前活动的功能模块，默认为概览页面

	const featureItems = [ // 功能项目配置数组，定义各种服务和功能的访问权限
		{ id: 'recharge', title: '充值', icon: '💰', gate: u => hasAnyRole(u, ['student', 'teacher', 'reviewer', 'academicAdmin', 'systemAdmin', 'superAdmin']), intent: 'openRecharge' }, // 充值功能，需要特定角色权限
		{ id: 'redeem', title: '兑换', icon: '🎁', gate: u => hasAnyRole(u, ['student', 'teacher', 'reviewer', 'academicAdmin', 'systemAdmin', 'superAdmin']), intent: 'openRedeem' }, // 兑换功能，需要特定角色权限
		{ id: 'coupons', title: '卡券', icon: '🎫', gate: u => hasAnyRole(u, ['student', 'teacher', 'reviewer', 'academicAdmin', 'systemAdmin', 'superAdmin']), intent: 'openCoupons' }, // 卡券功能，需要特定角色权限
		{ id: 'profile', title: '个人信息', icon: '👤', gate: u => !u.guest, intent: 'gotoProfile' }, // 个人信息功能，仅登录用户可用
		{ id: 'community', title: '加入社群', icon: '💬', gate: u => !u.guest, intent: 'joinCommunity' }, // 社群功能，仅登录用户可用
		{ id: 'checkin', title: '集点打卡', icon: '🗓️', gate: u => hasAnyRole(u, ['student', 'teacher', 'systemAdmin', 'superAdmin']), intent: 'openCheckin' }, // 打卡功能，需要特定角色权限
		{ id: 'questions', title: '题目管理', icon: '🗂️', gate: u => hasAnyRole(u, ['teacher', 'academicAdmin', 'systemAdmin', 'superAdmin']), intent: 'openQuestionManager' }, // 题目管理功能，仅教师及以上角色可用
		{ id: 'approvals', title: '角色审批', icon: '🛂', gate: u => hasAnyRole(u, ['systemAdmin', 'superAdmin']), intent: 'openRoleApprovals' }, // 角色审批功能，仅系统管理员可用
		{ id: 'stats', title: '统计', icon: '📊', gate: u => hasAnyRole(u, ['systemAdmin', 'superAdmin']), intent: 'openStats' }, // 统计功能，仅系统管理员可用
		{ id: 'review', title: '阅卷审核', icon: '📝', gate: u => hasAnyRole(u, ['reviewer', 'systemAdmin', 'superAdmin']), intent: 'openReviewCenter' }, // 阅卷审核功能，需要审核员权限
		{ id: 'sysFlags', title: '系统开关', icon: '⚙️', gate: u => hasAnyRole(u, ['superAdmin']), intent: 'openSystemFlags' }, // 系统开关功能，仅超级管理员可用
		{ id: 'auditLogs', title: '审计日志', icon: '📜', gate: u => hasAnyRole(u, ['superAdmin']), intent: 'openAuditLogs' }, // 审计日志功能，仅超级管理员可用
		{ id: 'maintenance', title: '维护模式', icon: '🛠️', gate: u => hasAnyRole(u, ['superAdmin']), intent: 'toggleMaintenance' }, // 维护模式功能，仅超级管理员可用
	];



	// ==================== 导航渲染器 ====================
	// 导航渲染器类，负责渲染个人中心的导航菜单
	class NavigationRenderer {
		static render() { // 渲染导航菜单的静态方法
			const nav = PersonalCenterDOMUtils.getElement('pc-nav'); // 获取导航容器元素
			if (!nav) { return; } // 如果导航容器不存在，直接返回

			const visible = sections.filter(s => s.gate(userContext)); // 根据用户权限过滤可见的导航项
			nav.innerHTML = visible // 设置导航容器的HTML内容
				.map(s => `<button class="pc-nav-item${s.id === activeSection ? ' active' : ''}" data-sec="${s.id}">${s.title}</button>`) // 将每个导航项映射为按钮HTML，当前活动项添加active类
				.join(''); // 将所有按钮HTML连接成字符串

			PersonalCenterDOMUtils.addEventListeners(nav, { // 为导航容器添加点击事件监听器
				'click': (e) => { // 定义点击事件处理函数
					const btn = e.target.closest('button.pc-nav-item'); // 查找最近的导航按钮元素
					if (!btn) { return; } // 如果没有找到按钮，直接返回

					activeSection = btn.getAttribute('data-sec'); // 获取按钮的数据属性，设置为当前活动区域
					this.render(); // 重新渲染导航菜单以更新活动状态
					renderActiveSection(); // 渲染对应的内容区域
				}
			});
		}
	}

	function renderSectionsNav() { // 渲染导航菜单的包装函数
		NavigationRenderer.render(); // 调用导航渲染器的渲染方法
	}

	// ==================== 身份渲染器 ====================
	// 身份渲染器类，负责渲染用户身份信息、头像和用户选择器
	class IdentityRenderer {
		static async render() { // 异步渲染身份信息的主方法
			const elements = this.getRequiredElements(); // 获取渲染所需的DOM元素
			if (!elements) { return; } // 如果必需元素不存在，直接返回

			await dataManager.loadAllUsers(); // 异步加载所有用户数据
			log('Rendering identity, allUsers length:', dataManager.allUsers.length, 'userContext:', userContext); // 记录渲染开始和相关数据

			if (userContext.guest) { // 如果当前用户是访客状态
				this.renderGuestIdentity(elements); // 渲染访客身份信息
				return; // 访客渲染完成，直接返回
			}

			this.renderUserIdentity(elements); // 渲染已登录用户的身份信息
			this.renderUserSelector(elements); // 渲染用户选择器下拉菜单
			this.renderAvatar(elements.avatarEl); // 渲染用户头像
		}

		static getRequiredElements() { // 获取渲染身份信息所需的DOM元素
			const nameEl = PersonalCenterDOMUtils.getElement('pc-name'); // 获取用户名显示元素
			const rolesEl = PersonalCenterDOMUtils.getElement('pc-roles'); // 获取角色显示元素
			const avatarEl = PersonalCenterDOMUtils.getElement('pc-avatar'); // 获取头像显示元素

			if (!nameEl || !rolesEl || !avatarEl) { // 如果任何必需元素不存在
				log('Required identity elements not found'); // 记录元素缺失的警告
				return null; // 返回null表示获取失败
			}

			return { nameEl, rolesEl, avatarEl }; // 返回包含所有必需元素的对象
		}

		static renderGuestIdentity({ nameEl, rolesEl, avatarEl }) { // 渲染访客身份信息的方法
			nameEl.textContent = '未登录'; // 设置用户名显示为"未登录"
			rolesEl.textContent = ''; // 清空角色显示内容
			avatarEl.textContent = 'G'; // 设置头像显示为字母"G"（Guest的首字母）
		}

		static renderUserIdentity({ nameEl, rolesEl }) { // 渲染已登录用户身份信息的方法
			nameEl.textContent = userContext.displayName || '用户'; // 设置用户名显示，如果没有显示名则使用"用户"
			rolesEl.textContent = ''; // 清空角色显示内容（角色信息在其他地方显示）
		}

		static renderUserSelector({ nameEl }) { // 渲染用户选择器下拉菜单的方法
			// 移除旧的选择器，确保不会重复创建
			const oldSelect = nameEl.parentNode.querySelector('select.pc-user-switch'); // 查找已存在的用户切换选择器
			if (oldSelect) { oldSelect.remove(); } // 如果存在旧选择器，将其移除

			const select = this.createUserSelector(); // 创建新的用户选择器
			this.insertUserSelector(nameEl, select); // 将选择器插入到合适的位置
		}

		static createUserSelector() { // 创建用户选择器下拉菜单的方法
			const select = PersonalCenterDOMUtils.createElement('select', 'pc-user-switch'); // 创建select元素，设置CSS类名
			Object.assign(select.style, { // 批量设置选择器的样式属性
				fontSize: 'inherit', // 继承父元素的字体大小
				margin: '0 0 0 4px' // 设置左边距为4像素
			});

			if (dataManager.allUsers.length === 0) { // 如果没有用户数据
				const opt = PersonalCenterDOMUtils.createElement('option'); // 创建选项元素
				Object.assign(opt, { // 批量设置选项的属性
					value: '', // 设置选项值为空字符串
					textContent: '无用户', // 设置选项显示文本
					disabled: true, // 禁用该选项
					selected: true // 设置为默认选中
				});
				select.appendChild(opt); // 将选项添加到选择器中
			} else { // 如果有用户数据
				dataManager.allUsers.forEach(u => { // 遍历所有用户数据
					const opt = PersonalCenterDOMUtils.createElement('option'); // 为每个用户创建选项元素
					Object.assign(opt, { // 批量设置选项属性
						value: u.id, // 设置选项值为用户ID
						textContent: u.displayName ? `${u.displayName} (${u.id})` : u.id, // 设置显示文本，优先显示用户名，否则显示ID
						selected: u.id === userContext.id // 如果是当前用户则设置为选中状态
					});
					select.appendChild(opt); // 将选项添加到选择器中
				});
			}

			PersonalCenterDOMUtils.addEventListeners(select, { // 为选择器添加事件监听器
				'change': (e) => { // 定义选择器值改变时的处理函数
					const uid = select.value; // 获取选择器当前选中的用户ID
					const u = dataManager.allUsers.find(x => x.id === uid); // 根据ID查找对应的用户数据
					if (u) { // 如果找到了用户数据
						window.setUserContext({ // 调用全局方法设置用户上下文
							id: u.id, // 设置用户ID
							displayName: u.displayName, // 设置用户显示名
							roles: u.roleIds, // 设置用户角色数组
							balance: u.balance, // 设置用户余额信息
							email: u.email, // 设置用户邮箱
							avatar: u.avatar, // 设置用户头像
							lastLoginAt: u.lastLoginAt, // 设置最后登录时间
							status: u.status, // 设置用户状态
							accessibleLevels: u.accessibleLevels, // 设置用户可访问的级别
							guest: false // 设置为非访客状态
						});
					}
				}
			});

			return select; // 返回创建的选择器元素
		}

		static insertUserSelector(nameEl, select) { // 将用户选择器插入到合适位置的方法
			if (nameEl.nextSibling) { // 如果用户名元素有下一个兄弟节点
				nameEl.parentNode.insertBefore(select, nameEl.nextSibling); // 在下一个兄弟节点之前插入选择器
			} else { // 如果没有下一个兄弟节点
				nameEl.parentNode.appendChild(select); // 直接添加到父节点的末尾
			}
		}

		static renderAvatar(avatarEl) { // 渲染用户头像的方法
			log('User avatar:', userContext.avatar); // 记录用户头像信息用于调试
			if (userContext.avatar) { // 如果用户有头像URL
				avatarEl.innerHTML = `<img src="${userContext.avatar}" alt="avatar" style="width:40px;height:40px;border-radius:50%;object-fit:cover;" />`; // 创建img元素显示头像，设置为圆形样式
			} else { // 如果用户没有头像
				avatarEl.textContent = initials(userContext.displayName || 'U'); // 显示用户名的首字母，默认为'U'
			}
		}
	}

	async function renderIdentity() { // 异步渲染用户身份信息的函数
		await IdentityRenderer.render(); // 调用身份渲染器的render方法，等待渲染完成
	}

	function renderActiveSection() { // 渲染当前激活的个人中心内容区域
		const container = document.getElementById('pc-content'); // 获取个人中心内容容器元素
		if (!container) { return; } // 如果容器不存在则直接返回，防止空指针错误
		switch (activeSection) { // 根据当前激活的区域类型进行分支处理
			case 'dashboard': // 如果是仪表盘区域
				container.innerHTML = renderDashboard(); attachDashboardHandlers(container); break; // 渲染仪表盘HTML并绑定事件处理器
			case 'system-flags': // 如果是系统标志区域
				container.innerHTML = renderSystemFlags(); attachSystemFlagsHandlers(container); break; // 渲染系统标志HTML并绑定事件处理器
			case 'profile': // 如果是个人资料区域
				container.innerHTML = renderProfile(); break; // 渲染个人资料HTML
			case 'roles': // 如果是角色管理区域
				container.innerHTML = renderRoles(); attachRolesHandlers(container); break; // 渲染角色管理HTML并绑定事件处理器
			case 'community': // 如果是社区区域
				container.innerHTML = renderCommunity(); break; // 渲染社区HTML
			case 'balance': // 如果是余额区域
				container.innerHTML = renderBalance(); break; // 渲染余额HTML
			case 'admin-hub': // 如果是管理中心区域
				container.innerHTML = renderAdminHub(); break; // 渲染管理中心HTML
			case 'logout': // 如果是登出操作
				logoutUser(); return; // 执行登出用户操作并直接返回
			default: // 如果是未知的区域类型
				container.innerHTML = '<div class="pc-section">暂未实现</div>'; // 显示"暂未实现"提示
		}
		container.scrollTop = 0; // 将内容容器滚动到顶部，确保用户看到新内容的开头
	}

	let wechatState = { status: 'idle', sceneId: null, expireAt: 0, pollTimer: null, expireTimer: null }; // 微信登录状态对象：idle=空闲，sceneId=场景ID，expireAt=过期时间戳，pollTimer=轮询定时器，expireTimer=过期定时器

	function openWeChatLogin() { // 打开微信登录弹窗的函数
		ensureWeChatModal(); // 确保微信登录模态框已创建
		showWeChatModal(); // 显示微信登录模态框
		startWeChatFlow(); // 启动微信登录流程
	}

	function ensureWeChatModal() { // 确保微信登录模态框存在，如果不存在则创建
		if (document.getElementById('wechat-login-modal')) { return; } // 如果模态框已存在则直接返回，避免重复创建
		const wrap = document.createElement('div'); // 创建一个新的div元素作为模态框容器
		wrap.id = 'wechat-login-modal'; // 设置容器的ID为wechat-login-modal
		wrap.className = 'wechat-hidden'; // 设置初始类名为wechat-hidden，默认隐藏状态
		wrap.innerHTML = `
			<div class="wechat-backdrop" data-wc-act="close"></div>
			<div class="wechat-panel" role="dialog" aria-modal="true" aria-label="微信登录">
				<div class="wechat-header">
					<strong>微信扫码登录</strong>
					<button class="wechat-close" data-wc-act="close" aria-label="关闭">×</button>
				</div>
				<div class="wechat-body">
					<div class="wechat-qr-box" id="wechat-qr-box">
						<div class="wechat-qr-placeholder" id="wechat-qr-placeholder">生成中…</div>
					</div>
					<div class="wechat-status" id="wechat-status"></div>
				</div>
				<div class="wechat-footer">
					<button class="wc-btn" data-wc-act="refresh">刷新二维码</button>
					<button class="wc-btn" data-wc-act="cancel">取消</button>
				</div>
			</div>`; // 设置模态框的HTML结构：包含背景遮罩、面板、头部、二维码区域、状态显示和底部按钮
		document.body.appendChild(wrap); // 将模态框容器添加到页面body的末尾
		wrap.addEventListener('click', onWeChatModalClick, false); // 为模态框添加点击事件监听器，处理按钮点击
		document.addEventListener('keydown', onWeChatKey, false); // 为文档添加键盘事件监听器，处理ESC键关闭
	}

	function showWeChatModal() { // 显示微信登录模态框
		const m = document.getElementById('wechat-login-modal'); // 获取微信登录模态框元素
		if (!m) { return; } // 如果模态框不存在则直接返回
		m.classList.remove('wechat-hidden'); // 移除隐藏类名
		m.classList.add('wechat-open'); // 添加打开类名，触发显示动画
	}

	function hideWeChatModal() { // 隐藏微信登录模态框
		const m = document.getElementById('wechat-login-modal'); // 获取微信登录模态框元素
		if (!m) { return; } // 如果模态框不存在则直接返回
		m.classList.remove('wechat-open'); // 移除打开类名
		m.classList.add('wechat-hidden'); // 添加隐藏类名，触发隐藏动画
		stopWeChatPolling(); // 停止微信登录状态轮询
	}

	function onWeChatModalClick(e) { // 处理微信登录模态框内的点击事件
		const el = e.target; // 获取被点击的元素
		if (!(el instanceof HTMLElement)) { return; } // 如果不是HTML元素则直接返回
		const act = el.getAttribute('data-wc-act'); // 获取元素的data-wc-act属性，表示操作类型
		if (act === 'close' || act === 'cancel') { hideWeChatModal(); return; } // 如果是关闭或取消操作，隐藏模态框并返回
		if (act === 'refresh') { startWeChatFlow(true); } // 如果是刷新操作，强制重新启动微信登录流程
	}
	function onWeChatKey(e) { if (e.key === 'Escape') { hideWeChatModal(); } } // 处理键盘事件：按ESC键时隐藏微信登录模态框

	function startWeChatFlow(force) { // 启动微信登录流程，force参数表示是否强制重新开始
		if (wechatState.status === 'waiting' && !force) { return; } // 如果当前正在等待扫码且不是强制刷新，则直接返回避免重复请求
		stopWeChatPolling(); // 停止之前的轮询定时器
		wechatState = { status: 'fetching', sceneId: null, expireAt: 0, pollTimer: null, expireTimer: null }; // 重置微信状态为获取中
		updateWeChatStatus(); // 更新UI显示当前状态
		setTimeout(() => { // 使用setTimeout模拟异步请求延迟
			const sceneId = 'SCENE_' + Math.random().toString(36).slice(2, 10); // 生成随机场景ID，用于标识本次登录会话
			const expiresIn = 60; // 设置二维码有效期为60秒
			wechatState.sceneId = sceneId; // 保存场景ID到状态对象
			wechatState.status = 'waiting'; // 更新状态为等待扫码
			wechatState.expireAt = Date.now() + expiresIn * 1000; // 计算过期时间戳（当前时间+60秒）
			renderFakeQRCode(sceneId); // 渲染模拟的二维码
			updateWeChatStatus(); // 更新状态显示文本
			beginFakePolling(); // 开始模拟轮询登录状态
		}, 600); // 延迟600毫秒执行，模拟网络请求延迟
	}

	function renderFakeQRCode(sceneId) { // 渲染模拟的微信登录二维码
		const box = document.getElementById('wechat-qr-box'); // 获取二维码容器元素
		if (!box) { return; } // 如果容器不存在则直接返回
		box.innerHTML = ''; // 清空容器内容
		const cvs = document.createElement('canvas'); // 创建canvas元素用于绘制二维码
		cvs.width = 180; cvs.height = 180; // 设置canvas尺寸为180x180像素
		const ctx = cvs.getContext('2d'); // 获取2D绘图上下文
		if (ctx) { // 如果成功获取绘图上下文
			ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, 180, 180); // 填充白色背景
			ctx.fillStyle = '#000'; // 设置文字颜色为黑色
			ctx.font = '12px monospace'; // 设置字体为12像素等宽字体
			ctx.fillText('WECHAT QR', 40, 70); // 绘制"WECHAT QR"文字
			ctx.fillText(sceneId.slice(-6), 55, 95); // 绘制场景ID的后6位字符
			ctx.fillText('模拟', 70, 120); // 绘制"模拟"文字标识
		}
		box.appendChild(cvs); // 将canvas添加到容器中显示
	}

	function beginFakePolling() { // 开始模拟轮询微信登录状态
		setTimeout(() => { fakeLoginSuccess(); }, 1000); // 1秒后模拟登录成功
	}

	function stopWeChatPolling() { // 停止微信登录状态轮询
		if (wechatState.pollTimer) { clearInterval(wechatState.pollTimer); } // 如果轮询定时器存在则清除
		wechatState.pollTimer = null; // 将定时器引用设为null
	}

	function updateWeChatStatus() { // 更新微信登录状态显示文本
		const sEl = document.getElementById('wechat-status'); // 获取状态显示元素
		if (!sEl) { return; } // 如果元素不存在则直接返回
		let text = ''; // 初始化状态文本为空字符串
		switch (wechatState.status) { // 根据当前状态设置对应的提示文本
			case 'fetching': text = '正在获取二维码…'; break; // 获取二维码中
			case 'waiting': text = '请使用微信扫描二维码登录'; break; // 等待扫码
			case 'scanned': text = '已扫码，等待确认…'; break; // 已扫码待确认
			case 'confirming': text = '确认中…'; break; // 确认中
			case 'success': text = '登录成功'; break; // 登录成功
			case 'expired': text = '二维码已过期，请刷新'; break; // 二维码过期
			case 'error': text = '登录出错，请重试'; break; // 登录出错
			default: text = ''; // 默认为空
		}
		if (wechatState.status === 'waiting') { // 如果当前状态是等待扫码
			const left = Math.max(0, wechatState.expireAt - Date.now()); // 计算剩余有效时间（毫秒）
			text += `（${Math.ceil(left / 1000)}s）`; // 在文本后追加剩余秒数
		}
		sEl.textContent = text; // 更新状态元素的文本内容
	}

	async function fakeLoginSuccess() { // 模拟微信登录成功的异步函数
		wechatState.status = 'success'; // 更新状态为登录成功
		updateWeChatStatus(); // 更新UI显示状态

		await dataManager.loadAllUsers(); // 异步加载所有用户数据

		setTimeout(() => { // 延迟执行登录逻辑，模拟真实场景
			log('fakeLoginSuccess - allUsers length:', dataManager.allUsers.length); // 记录用户总数
			log('fakeLoginSuccess - allUsers content:', dataManager.allUsers); // 记录用户数据内容

			let user = dataManager.allUsers.find(u => u.id === 'superAdmin01'); // 查找ID为superAdmin01的用户
			log('fakeLoginSuccess - found user:', user); // 记录找到的用户信息

			if (!user) { // 如果未找到该用户
				user = { // 创建默认的超级管理员用户对象
					id: 'superAdmin01', // 用户ID
					displayName: '超级管理员0111', // 显示名称
					roleIds: ['superAdmin'], // 角色ID数组，包含超级管理员角色
					balance: { credits: 1000, updatedAt: new Date().toISOString() }, // 余额信息：1000积分
					email: 'superAdmin01@example.local', // 邮箱地址
					avatar: null, // 头像为空
					lastLoginAt: new Date().toLocaleString(), // 最后登录时间为当前时间
					status: 'active', // 账户状态为活跃
					accessibleLevels: ['*'] // 可访问级别为所有（*表示通配符）
				};
			}

			window.setUserContext({ // 调用全局方法设置用户上下文信息
				id: user.id, // 用户ID
				displayName: user.displayName, // 用户显示名称
				roles: user.roleIds, // 用户角色ID数组
				balance: user.balance || { credits: 0, updatedAt: new Date().toISOString() }, // 余额信息，如果不存在则使用默认值0
				email: user.email, // 用户邮箱
				avatar: user.avatar, // 用户头像
				lastLoginAt: new Date().toLocaleString(), // 最后登录时间
				status: user.status, // 账户状态
				accessibleLevels: user.accessibleLevels, // 可访问级别
				guest: false // 标记为非访客用户
			});

			window.dispatchEvent(new CustomEvent('user:login', { detail: user })); // 触发用户登录事件，传递用户详细信息
			hideWeChatModal(); // 隐藏微信登录模态框
			openPanel(); // 打开个人中心面板
		}, 600); // 延迟600毫秒执行，模拟真实登录流程
	}

	// ==================== 内容渲染器 ====================
	class ContentRenderer { // 内容渲染器类，负责渲染个人中心各个区域的HTML内容
		static getUserStats() { // 获取用户统计信息的静态方法
			return { // 返回包含用户各项统计数据的对象
				roles: escapeHtml((userContext.roles || []).join(', ') || '无'), // 用户角色列表，转义HTML并用逗号连接，无角色时显示"无"
				balance: userContext.balance ? userContext.balance.credits : 0, // 用户余额积分，不存在时默认为0
				points: userContext.stats ? (userContext.stats.points ?? 0) : 0, // 用户积分，不存在时默认为0
				coupons: userContext.coupons ? userContext.coupons.length : 0, // 用户优惠券数量，不存在时默认为0
				features: visibleFeatures(userContext) // 根据用户权限获取可见的功能列表
			};
		}

		static renderDashboard() { // 渲染仪表盘的静态方法
			const stats = this.getUserStats(); // 获取用户统计信息

			return `<div class="pc-dashboard">
				${this.renderDashboardCards(stats)}
				${this.renderServiceCard(stats.features)}
				${this.renderMetaCard(stats.roles)}
			</div>`; // 返回仪表盘HTML：包含统计卡片、服务卡片和元信息卡片
		}

		static renderDashboardCards({ balance, points, coupons }) { // 渲染仪表盘统计卡片的静态方法，接收余额、积分、优惠券参数
			return `<div class="pc-dashboard-cards">
				<div class="pc-card pc-balance-card">
					<div class="pc-stat-pair">
						<div class="stat-item">
							<div class="stat-label">我的余额</div>
							<div class="stat-value">¥${balance}</div>
							<button class="pc-inline-btn" data-fx="recharge">充值</button>
						</div>
						<div class="stat-divider"></div>
						<div class="stat-item">
							<div class="stat-label">我的积分</div>
							<div class="stat-value">${points}</div>
							<button class="pc-inline-btn" data-fx="redeem">兑换</button>
						</div>
					</div>
				</div>
				<div class="pc-card pc-coupon-card">
					<div class="coupon-row">
						<div class="coupon-count">
							<div class="coupon-label">我的卡券</div>
							<div class="coupon-value">${coupons} 张</div>
						</div>
						<button class="pc-text-link" data-fx="viewCouponExp">优惠券即将过期 ›</button>
					</div>
				</div>
			</div>`; // 返回包含余额卡片和优惠券卡片的HTML结构
		}

		static renderServiceCard(features) { // 渲染服务功能卡片的静态方法，接收功能列表参数
			return `<div class="pc-card pc-service-card">
				<div class="pc-service-header">服务 / 功能</div>
				<div class="pc-service-grid">
					${features.map(f => `
						<button class="service-item" data-feature="${f.id}" data-intent="${f.intent}" title="${escapeHtml(f.title)}">
							<div class="svc-icon">${f.icon}</div>
							<div class="svc-title">${escapeHtml(f.title)}</div>
						</button>`).join('')}
				</div>
			</div>`; // 遍历功能列表生成服务项按钮，包含图标和标题，并拼接成HTML字符串
		}

		static renderMetaCard(roles) { // 渲染元信息卡片的静态方法，接收角色参数
			const welcomeName = userContext.displayName ? '，' + escapeHtml(userContext.displayName) : ''; // 如果有显示名称则添加逗号前缀，否则为空
			return `<div class="pc-card pc-meta-card">
				<div class="pc-meta-line">欢迎${welcomeName}！</div>
				<div class="pc-meta-line">当前角色：${roles}</div>
				<div class="pc-meta-line subtle">更多功能将逐步开放。</div>
			</div>`; // 返回包含欢迎信息、角色信息和提示信息的元信息卡片HTML
		}

		static renderProfile() { // 渲染个人资料页面的静态方法
			return `<div class="pc-section"><h2>个人资料</h2>
				<p>昵称：${escapeHtml(userContext.displayName || '未设置')}</p>
				<p>UID：${escapeHtml(userContext.id || '-')}</p>
				<p>最近登录：${escapeHtml(userContext.lastLoginAt || '-')}</p>
				<p><button disabled>修改资料（占位）</button></p>
			</div>`; // 返回包含昵称、UID、最近登录时间和修改按钮的个人资料HTML
		}

		static renderBalance() { // 渲染账户余额页面的静态方法
			const balance = userContext.balance ? (userContext.balance.credits + ' 点') : '—'; // 获取余额积分，不存在时显示破折号
			return `<div class="pc-section"><h2>账户</h2>
				<p>余额：${balance}</p>
				<p><button disabled>充值（占位）</button></p>
			</div>`; // 返回包含余额信息和充值按钮的账户HTML
		}
	}

	function renderDashboard() { // 渲染仪表盘的函数
		return ContentRenderer.renderDashboard(); // 调用ContentRenderer的静态方法渲染仪表盘
	}

	function renderProfile() { // 渲染个人资料的函数
		return ContentRenderer.renderProfile(); // 调用ContentRenderer的静态方法渲染个人资料
	}

	function renderBalance() { // 渲染账户余额的函数
		return ContentRenderer.renderBalance(); // 调用ContentRenderer的静态方法渲染账户余额
	}

	function renderRoles() { // 渲染角色管理页面的函数
		const owned = (userContext.roles || []); // 获取当前用户拥有的角色数组，不存在时使用空数组
		const ownedStr = escapeHtml(owned.join(', ') || '无'); // 将角色数组转为逗号分隔的字符串并转义HTML，无角色时显示"无"
		const isSuper = owned.includes('superAdmin'); // 判断当前用户是否为超级管理员
		let extra = ''; // 初始化额外内容为空字符串
		if (isSuper) { // 如果是超级管理员
			const allRoles = [ // 定义所有系统角色的配置数组
				{ id: 'guest', name: '访客', desc: '未登录，仅可浏览公开内容', risk: 'low' }, // 访客角色：低风险
				{ id: 'student', name: '学生', desc: '做题 / 积分 / 充值', risk: 'low' }, // 学生角色：低风险
				{ id: 'teacher', name: '教师', desc: '组卷 / 题库管理 / 布置', risk: 'medium' }, // 教师角色：中等风险
				{ id: 'reviewer', name: '阅卷', desc: '阅卷审核、质检', risk: 'medium' }, // 阅卷角色：中等风险
				{ id: 'academicAdmin', name: '教务', desc: '课程/科目/班级高级配置', risk: 'medium' }, // 教务角色：中等风险
				{ id: 'systemAdmin', name: '系统管理员', desc: '系统级管理（非高危开关）', risk: 'high' }, // 系统管理员角色：高风险
				{ id: 'superAdmin', name: '超级管理员', desc: '全部权限 + 高危系统操作', risk: 'critical' } // 超级管理员角色：严重风险
			];
			const rows = allRoles.map(r => `<tr>
				<td>${escapeHtml(r.id)}</td>
				<td>${escapeHtml(r.name)}</td>
				<td>${escapeHtml(r.desc)}</td>
				<td><span class="risk-badge role-risk-${r.risk}">${r.risk}</span></td>
				<td>${owned.includes(r.id) ? '<span class="role-owned">✔</span>' : ''}</td>
			</tr>`).join(''); // 遍历角色数组生成表格行，包含ID、名称、描述、风险等级和拥有状态
			const roleBlocks = allRoles.map(r => { // 遍历角色数组生成角色用户块
				const users = dataManager.getUsersByRole(r.id); // 获取拥有该角色的所有用户
				if (!users.length) { return ''; } // 如果没有用户则返回空字符串
				const head = `<div class="role-users-head"><strong>${escapeHtml(r.name)}</strong><span class="ru-count">(${users.length})</span></div>`; // 生成角色头部：角色名称和用户数量
				const listItems = users.slice(0, 5).map(u => `<li data-impersonate="${escapeHtml(u.id)}" title="切换为该用户">
					<span class="ru-name">${escapeHtml(u.displayName)}</span>
					<span class="ru-id">${escapeHtml(u.id)}</span>
				</li>`).join(''); // 生成前5个用户的列表项，包含用户名和ID，支持切换用户功能
				const more = users.length > 5 ? `<div class="ru-more">+${users.length - 5} 更多…</div>` : ''; // 如果用户超过5个则显示"更多"提示
				return `<div class="role-users-block" data-role="${escapeHtml(r.id)}">${head}<ul class="role-user-list">${listItems}</ul>${more}</div>`; // 返回完整的角色用户块HTML
			}).join(''); // 拼接所有角色用户块
			extra = `<h3 style="margin-top:16px;">系统角色总览（仅 superAdmin 可见）</h3>
			<table class="roles-table"><thead><tr><th>ID</th><th>名称</th><th>说明</th><th>风险</th><th>拥有</th></tr></thead><tbody>${rows}</tbody></table>
			<p class="subtle" style="margin-top:8px;">下方是各角色的模拟用户（点击可快速切换身份，仅前端）。</p>
			<div class="role-users-grid">${roleBlocks}</div>`; // 生成角色总览表格和用户列表的HTML，包含角色信息表格和可切换身份的用户列表
		}
		return `<div class="pc-section"><h2>角色与权限</h2>
			<p>已拥有角色：${ownedStr}</p>
			<p><button disabled>申请教师（占位）</button> <button disabled>申请阅卷（占位）</button></p>
			${extra}
		</div>`; // 返回角色与权限页面HTML，包含已拥有角色、申请按钮和额外的超管专属内容
	}

	function renderCommunity() { // 渲染社群页面的函数
		return `<div class="pc-section"><h2>社群</h2>
			<p>加入学习社群以获取更多资料。</p>
			<p><button disabled>加入社群（占位）</button></p>
		</div>`; // 返回社群页面HTML，包含说明文字和加入按钮（占位）
	}

	function renderAdminHub() { // 渲染管理面板页面的函数
		return `<div class="pc-section"><h2>管理面板</h2>
			<ul>
				<li><button disabled>题目管理（占位）</button></li>
				<li><button disabled>角色审批（占位）</button></li>
				<li><button disabled>统计报表（占位）</button></li>
			</ul>
		</div>`; // 返回管理面板HTML，包含题目管理、角色审批、统计报表等功能按钮（占位）
	}





	function handleFeatureIntent(intent) { // 处理功能意图的函数，根据不同的intent执行相应操作
		switch (intent) { // 根据intent参数进行分支处理
			case 'gotoProfile': activeSection = 'profile'; renderActiveSection(); renderSectionsNav(); break; // 跳转到个人资料页面，更新激活区域并重新渲染
			case 'joinCommunity': showToast('加入社群占位'); break; // 显示加入社群的占位提示
			case 'openRecharge': showToast('充值占位'); break; // 显示充值的占位提示
			case 'openRedeem': showToast('兑换占位'); break; // 显示兑换的占位提示
			case 'openCoupons': showToast('卡券占位'); break; // 显示卡券的占位提示
			case 'openCheckin': showToast('集点打卡占位'); break; // 显示集点打卡的占位提示
			case 'openQuestionManager': showToast('题目管理占位'); break; // 显示题目管理的占位提示
			case 'openRoleApprovals': showToast('角色审批占位'); break; // 显示角色审批的占位提示
			case 'openStats': showToast('统计占位'); break; // 显示统计的占位提示
			case 'openReviewCenter': showToast('阅卷中心占位'); break; // 显示阅卷中心的占位提示
			case 'openSystemFlags': activeSection = 'system-flags'; renderActiveSection(); renderSectionsNav(); break; // 跳转到系统标志页面，更新激活区域并重新渲染
			case 'openAuditLogs': showToast('审计日志占位'); break; // 显示审计日志的占位提示
			case 'toggleMaintenance': ensureSystemState(); confirmRiskAction({ // 切换维护模式，先确保系统状态存在，然后显示风险确认对话框
				actionLabel: systemState.maintenance ? '关闭维护模式' : '开启维护模式', // 根据当前状态设置操作标签
				riskLevel: 'high', // 设置风险等级为高
				confirmWord: 'MAINTAIN', // 设置确认关键词为MAINTAIN
				description: '维护模式会让普通用户无法正常使用（只读或提示维护），请确认当前无进行中的高风险写入任务。', // 操作描述和警告
				onConfirm: () => { // 确认后的回调函数
					systemState.maintenance = !systemState.maintenance; // 切换维护模式状态
					showToast('（模拟）维护模式已' + (systemState.maintenance ? '开启' : '关闭')); // 显示操作结果提示
					if (activeSection === 'system-flags') { renderActiveSection(); } // 如果当前在系统标志页面则重新渲染
				}
			}); break;
			default: showToast('未识别 intent: ' + intent); // 默认情况：显示未识别的intent提示
		}
	}

	// ==================== 事件处理器管理器 ====================
	class EventHandlerManager { // 事件处理器管理器类，负责为不同区域绑定事件处理器
		static attachDashboardHandlers(root) { // 为仪表盘区域绑定事件处理器的静态方法
			// 功能按钮处理
			PersonalCenterDOMUtils.addEventListeners(root, { // 使用工具类为根元素添加事件监听器
				'click': (e) => { // 点击事件处理函数
					const target = e.target; // 获取被点击的目标元素

					// 处理功能按钮
					const fxButton = target.closest('[data-fx]'); // 查找最近的带有data-fx属性的祖先元素
					if (fxButton) { // 如果找到功能按钮
						showToast('功能占位: ' + fxButton.getAttribute('data-fx')); // 显示功能占位提示
						return; // 返回，不再继续处理
					}

					// 处理服务项目
					const serviceItem = target.closest('button.service-item'); // 查找最近的服务项按钮
					if (serviceItem) { // 如果找到服务项按钮
						const intent = serviceItem.getAttribute('data-intent'); // 获取服务项的intent属性
						handleFeatureIntent(intent); // 调用功能意图处理函数
						return; // 返回，不再继续处理
					}
				}
			});
		}

		static attachRolesHandlers(root) { // 为角色管理区域绑定事件处理器的静态方法
			const roleGrid = root.querySelector('.role-users-grid'); // 查找角色用户网格容器
			if (!roleGrid) { return; } // 如果容器不存在则直接返回

			PersonalCenterDOMUtils.addEventListeners(roleGrid, { // 为角色网格添加事件监听器
				'click': (e) => { // 点击事件处理函数
					const el = e.target.closest('li[data-impersonate]'); // 查找最近的带有data-impersonate属性的li元素
					if (!el) { return; } // 如果未找到则返回

					const uid = el.getAttribute('data-impersonate'); // 获取要切换的用户ID
					if (!uid) { return; } // 如果用户ID不存在则返回

					const target = dataManager.allUsers.find(u => u.id === uid); // 从所有用户中查找目标用户
					if (!target) { return; } // 如果未找到目标用户则返回

					showToast('切换为 ' + target.displayName); // 显示切换用户的提示
					window.setUserContext({ ...target }); // 设置新的用户上下文（展开目标用户对象）
					renderIdentity(); // 重新渲染用户身份信息
					renderSectionsNav(); // 重新渲染导航区域
					if (activeSection === 'roles') { // 如果当前在角色管理页面
						renderActiveSection(); // 重新渲染当前区域内容
					}
				}
			});
		}

		static attachSystemFlagsHandlers(root) { // 为系统标志区域绑定事件处理器的静态方法
			// 维护模式按钮
			const maintenanceBtn = root.querySelector('[data-maintenance]'); // 查找维护模式按钮
			if (maintenanceBtn) { // 如果按钮存在
				PersonalCenterDOMUtils.addEventListeners(maintenanceBtn, { // 为按钮添加事件监听器
					'click': () => handleFeatureIntent('toggleMaintenance') // 点击时调用切换维护模式的功能意图
				});
			}

			// 功能开关按钮
			root.querySelectorAll('.sf-toggle').forEach(btn => { // 遍历所有功能开关按钮
				PersonalCenterDOMUtils.addEventListeners(btn, { // 为每个按钮添加事件监听器
					'click': () => { // 点击事件处理函数
						const key = btn.getAttribute('data-flag'); // 获取功能标志的key
						const risk = btn.getAttribute('data-risk'); // 获取风险等级
						ensureSystemState(); // 确保系统状态对象存在
						const flag = systemState.flags.find(f => f.key === key); // 从系统状态中查找对应的功能标志
						if (!flag) { return; } // 如果未找到则返回

						confirmRiskAction({ // 显示风险确认对话框
							actionLabel: (flag.value ? '关闭 ' : '开启 ') + key, // 根据当前状态设置操作标签
							riskLevel: risk, // 设置风险等级
							confirmWord: risk === 'high' ? key.toUpperCase() : null, // 高风险操作需要输入确认关键词（key的大写形式）
							description: '切换开关会立即影响相关功能行为（本地模拟）。', // 操作描述
							onConfirm: () => { // 确认后的回调函数
								flag.value = !flag.value; // 切换功能标志的值
								showToast(key + ' => ' + (flag.value ? 'ON' : 'OFF')); // 显示切换结果提示
								if (activeSection === 'system-flags') { // 如果当前在系统标志页面
									renderActiveSection(); // 重新渲染当前区域内容
								}
							}
						});
					}
				});
			});
		}
	}

	function attachDashboardHandlers(root) { // 为仪表盘绑定事件处理器的函数
		EventHandlerManager.attachDashboardHandlers(root); // 调用事件处理器管理器的静态方法
	}

	function attachRolesHandlers(root) { // 为角色管理绑定事件处理器的函数
		EventHandlerManager.attachRolesHandlers(root); // 调用事件处理器管理器的静态方法
	}

	function attachSystemFlagsHandlers(root) { // 为系统标志绑定事件处理器的函数
		EventHandlerManager.attachSystemFlagsHandlers(root); // 调用事件处理器管理器的静态方法
	}

	let systemState = null; // 系统状态对象，初始为null，用于存储维护模式和功能开关状态
	function ensureSystemState() { // 确保系统状态对象存在的函数
		if (!systemState) { // 如果系统状态对象不存在
			systemState = { // 创建默认的系统状态对象
				maintenance: false, // 维护模式默认关闭
				flags: [ // 功能开关数组
					{ key: 'maintenanceMode', value: false, desc: '全站维护模式', risk: 'high' }, // 全站维护模式开关：高风险
					{ key: 'betaNewEditor', value: true, desc: '新编辑器灰度', risk: 'medium' }, // 新编辑器灰度开关：中等风险
					{ key: 'enableWeChatLogin', value: true, desc: '启用微信登录', risk: 'low' } // 微信登录开关：低风险
				]
			};
		}
	}

	function renderSystemFlags() { // 渲染系统标志页面的函数
		ensureSystemState(); // 确保系统状态对象存在
		const rows = systemState.flags.map(f => `<tr data-key="${f.key}">
		<td class="sf-key">${escapeHtml(f.key)}</td>
		<td class="sf-desc">${escapeHtml(f.desc)}</td>
		<td class="sf-val"><span class="flag-val ${f.value ? 'on' : 'off'}">${f.value ? 'ON' : 'OFF'}</span></td>
		<td class="sf-risk"><span class="risk-badge risk-${f.risk}">${f.risk}</span></td>
		<td class="sf-act"><button class="sf-toggle" data-flag="${f.key}" data-risk="${f.risk}">${f.value ? '关闭' : '开启'}</button></td>
	</tr>`).join(''); // 遍历功能开关数组生成表格行，包含key、描述、当前值、风险等级和操作按钮
		return `<div class="pc-section system-flags">
		<h2>系统开关 / 运维</h2>
		<div class="maintenance-card">
			<div class="mc-left">
				<div class="mc-title">维护模式</div>
				<div class="mc-desc">当前：<strong>${systemState.maintenance ? '开启' : '关闭'}</strong>。开启后普通用户访问将受限。</div>
			</div>
			<div class="mc-right">
				<button class="mc-toggle" data-maintenance>${systemState.maintenance ? '关闭维护' : '开启维护'}</button>
			</div>
		</div>
		<h3>功能开关</h3>
		<table class="sf-table">
			<thead><tr><th>Key</th><th>描述</th><th>值</th><th>风险</th><th>操作</th></tr></thead>
			<tbody>${rows}</tbody>
		</table>
		<p class="sf-hint">以上为本地模拟数据，后续将接入后端 API（GET/PUT /admin/feature-flags）。风险级别 high 需要输入确认词。</p>
	</div>`; // 返回系统标志页面HTML，包含维护模式卡片、功能开关表格和提示信息
	}

	function attachSystemFlagsHandlers(root) { // 为系统标志页面绑定事件处理器的函数（重复定义，可能是遗留代码）
		root.querySelector('[data-maintenance]')?.addEventListener('click', () => handleFeatureIntent('toggleMaintenance')); // 为维护模式按钮添加点击事件监听器

	}

	let riskModalEl = null; // 风险确认模态框元素，初始为null
	function ensureRiskModal() { // 确保风险确认模态框存在的函数
		if (riskModalEl) { return riskModalEl; } // 如果模态框已存在则直接返回
		riskModalEl = document.createElement('div'); // 创建一个新的div元素作为模态框容器
		riskModalEl.id = 'risk-modal'; // 设置容器ID为risk-modal
		riskModalEl.className = 'risk-hidden'; // 设置初始类名为risk-hidden，默认隐藏状态
		riskModalEl.innerHTML = `<div class="risk-backdrop" data-rm-act="close"></div>
	<div class="risk-panel" role="dialog" aria-modal="true" aria-label="风险操作确认">
		<div class="risk-header"><strong id="risk-title">操作确认</strong><button class="risk-close" data-rm-act="close">×</button></div>
		<div class="risk-body" id="risk-body"></div>
		<div class="risk-footer" id="risk-footer"></div>
	</div>`; // 设置模态框的HTML结构：包含背景遮罩、面板、头部、内容区域和底部区域
		document.body.appendChild(riskModalEl); // 将模态框容器添加到页面body的末尾
		riskModalEl.addEventListener('click', onRiskModalClick, false); // 为模态框添加点击事件监听器
		document.addEventListener('keydown', onRiskKey, false); // 为文档添加键盘事件监听器，处理ESC键关闭
		return riskModalEl; // 返回创建的模态框元素
	}

	function confirmRiskAction(opts) { // 显示风险确认对话框的函数，接收配置选项对象
		const { actionLabel, riskLevel, confirmWord, description, onConfirm } = opts; // 解构配置选项：操作标签、风险等级、确认关键词、描述、确认回调
		ensureRiskModal(); // 确保风险确认模态框存在
		const panel = riskModalEl.querySelector('.risk-panel'); // 获取模态框面板元素
		const titleEl = riskModalEl.querySelector('#risk-title'); // 获取标题元素
		const bodyEl = riskModalEl.querySelector('#risk-body'); // 获取内容区域元素
		const footerEl = riskModalEl.querySelector('#risk-footer'); // 获取底部区域元素
		let countdown = riskLevel === 'high' ? 5 : 0; // 高风险操作需要5秒倒计时，其他操作无需倒计时
		let timer = null; // 倒计时定时器，初始为null
		const requiredWord = confirmWord || 'CONFIRM'; // 确认关键词，如果未提供则使用默认值'CONFIRM'
		let inputVal = ''; // 用户输入的确认关键词，初始为空字符串
		function updateConfirmState() { // 更新确认按钮状态的内部函数
			const btn = footerEl.querySelector('button[data-rm-act="confirm"]'); // 获取确认按钮元素
			const allow = (countdown === 0) && (riskLevel !== 'high' || inputVal === requiredWord); // 判断是否允许确认：倒计时结束且（非高风险或输入正确）
			btn.disabled = !allow; // 设置按钮的禁用状态
			if (riskLevel === 'high') { // 如果是高风险操作
				btn.textContent = allow ? actionLabel : actionLabel + ` (${countdown || '等待输入'})`; // 显示操作标签和倒计时或等待输入提示
			} else if (countdown > 0) { // 如果有倒计时
				btn.textContent = actionLabel + ` (${countdown})`; // 显示操作标签和倒计时秒数
			}
		}
		bodyEl.innerHTML = `<div class="risk-desc">${escapeHtml(description || '请确认执行该操作。')}</div>
		<div class="risk-level">风险等级: <span class="risk-tag risk-${riskLevel}">${riskLevel.toUpperCase()}</span></div>
		${riskLevel === 'high' ? `<div class="risk-input-row">请输入 <code>${requiredWord}</code> 以确认：<input id="risk-input" class="risk-input" placeholder="${requiredWord}" /></div>` : ''}`; // 设置内容区域HTML：描述、风险等级标签，高风险操作需要输入确认关键词
		footerEl.innerHTML = `<button class="risk-btn" data-rm-act="cancel">取消</button><button class="risk-btn primary" data-rm-act="confirm" disabled>${actionLabel}${countdown ? ` (${countdown})` : ''}</button>`; // 设置底部区域HTML：取消按钮和确认按钮（初始禁用）
		riskModalEl.classList.remove('risk-hidden'); // 移除隐藏类名
		riskModalEl.classList.add('risk-open'); // 添加打开类名，显示模态框
		titleEl.textContent = actionLabel; // 设置标题文本为操作标签
		if (riskLevel === 'high' || countdown > 0) { // 如果是高风险操作或有倒计时
			timer = setInterval(() => { // 创建定时器，每秒执行一次
				if (countdown > 0) { countdown--; updateConfirmState(); } // 如果倒计时未结束则减1并更新按钮状态
				if (countdown <= 0 && timer) { clearInterval(timer); timer = null; updateConfirmState(); } // 倒计时结束时清除定时器并更新按钮状态
			}, 1000); // 每1000毫秒（1秒）执行一次
		}
		const input = riskModalEl.querySelector('#risk-input'); // 获取确认关键词输入框元素
		if (input) { // 如果输入框存在（高风险操作）
			input.addEventListener('input', () => { inputVal = input.value.trim(); updateConfirmState(); }); // 监听输入事件，更新输入值并刷新按钮状态
			setTimeout(() => input.focus(), 30); // 延迟30毫秒后自动聚焦到输入框
		}
		footerEl.querySelector('[data-rm-act="confirm"]').addEventListener('click', () => { // 为确认按钮添加点击事件监听器
			if (timer) { clearInterval(timer); } // 如果定时器存在则清除
			riskModalEl.classList.remove('risk-open'); // 移除打开类名
			riskModalEl.classList.add('risk-hidden'); // 添加隐藏类名，关闭模态框
			try { onConfirm && onConfirm(); } catch (e) { console.error(e); } // 尝试执行确认回调函数，捕获并记录错误
		});
		footerEl.querySelector('[data-rm-act="cancel"]').addEventListener('click', () => { // 为取消按钮添加点击事件监听器
			if (timer) { clearInterval(timer); } // 如果定时器存在则清除
			riskModalEl.classList.remove('risk-open'); // 移除打开类名
			riskModalEl.classList.add('risk-hidden'); // 添加隐藏类名，关闭模态框
		});
		function cleanupOnClose() { if (timer) { clearInterval(timer); } } // 关闭时的清理函数，清除定时器
		riskModalEl.dataset.cleanup = '1'; // 设置数据属性标记需要清理
		riskModalEl._cleanup = cleanupOnClose; // 将清理函数保存到元素的自定义属性
		updateConfirmState(); // 初始化按钮状态
	}

	function onRiskModalClick(e) { // 处理风险确认模态框的点击事件
		const el = e.target; // 获取被点击的元素
		if (!(el instanceof HTMLElement)) { return; } // 如果不是HTML元素则直接返回
		const act = el.getAttribute('data-rm-act'); // 获取元素的data-rm-act属性，表示操作类型
		if (act === 'close' || act === 'cancel') { // 如果是关闭或取消操作
			closeRiskModal(); // 关闭风险确认模态框
		}
	}
	function onRiskKey(e) { if (e.key === 'Escape' && riskModalEl?.classList.contains('risk-open')) { closeRiskModal(); } } // 处理键盘事件：按ESC键且模态框打开时关闭模态框
	function closeRiskModal() { // 关闭风险确认模态框的函数
		if (!riskModalEl) { return; } // 如果模态框不存在则直接返回
		if (riskModalEl._cleanup) { try { riskModalEl._cleanup(); } catch { } } // 如果存在清理函数则执行，捕获可能的错误
		riskModalEl.classList.remove('risk-open'); // 移除打开类名
		riskModalEl.classList.add('risk-hidden'); // 添加隐藏类名，隐藏模态框
	}



	document.addEventListener('DOMContentLoaded', () => safeBuildTrigger('fallback-listener')); // DOM加载完成后的回退监听器，确保触发器被创建

	// ==================== 工具函数 ====================
	class PersonalCenterUtils { // 个人中心工具类，提供各种实用方法
		static escapeHtml(str) { // 转义HTML特殊字符的静态方法，防止XSS攻击
			return String(str).replace(/[&<>'"`]/g, c => ({ // 将字符串转为String类型并替换特殊字符
				'&': '&amp;', '<': '&lt;', '>': '&gt;', // HTML实体转义映射
				'\'': '&#39;', '"': '&quot;', '`': '&#96;' // 单引号、双引号、反引号的转义
			}[c] || c)); // 从映射对象中获取转义后的字符，如果不在映射中则保持原样
		}

		static initials(name) { // 获取用户名首字母的静态方法
			if (!name) { return 'U'; } // 如果名称为空则返回默认字母'U'
			const parts = name.trim().split(/\s+/); // 去除首尾空格并按空白字符分割名称
			if (parts.length === 1) { return parts[0].charAt(0).toUpperCase(); } // 如果只有一个单词则返回首字母大写
			return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase(); // 如果有多个单词则返回首尾单词的首字母大写组合
		}

		static showToast(msg) { // 显示提示消息的静态方法
			let el = PersonalCenterDOMUtils.getElement('pc-toast'); // 获取提示消息元素
			if (!el) { // 如果元素不存在
				el = PersonalCenterDOMUtils.createElement('div', 'pc-toast'); // 创建新的div元素并添加类名
				el.id = 'pc-toast'; // 设置元素ID
				document.body.appendChild(el); // 将元素添加到页面body
			}
			el.textContent = msg; // 设置提示消息文本
			PersonalCenterDOMUtils.toggleClass(el, 'show', true); // 添加show类名显示提示
			setTimeout(() => PersonalCenterDOMUtils.toggleClass(el, 'show', false), 2000); // 2秒后移除show类名隐藏提示
		}

		static hasAnyRole(u, roles) { // 判断用户是否拥有指定角色之一的静态方法
			if (!u || !Array.isArray(u.roles)) { return false; } // 如果用户不存在或角色不是数组则返回false
			return u.roles.some(r => roles.includes(r)); // 判断用户角色数组中是否包含指定角色中的任意一个
		}

		static visibleFeatures(u) { // 获取用户可见功能列表的静态方法
			return featureItems.filter(f => f.gate(u)); // 过滤功能列表，只返回通过权限检查的功能
		}
	}

	// 重新定义全局函数使用工具类
	function escapeHtml(str) { // 全局HTML转义函数
		return PersonalCenterUtils.escapeHtml(str); // 调用工具类的静态方法
	}

	function initials(name) { // 全局获取首字母函数
		return PersonalCenterUtils.initials(name); // 调用工具类的静态方法
	}

	function showToast(msg) { // 全局显示提示函数
		PersonalCenterUtils.showToast(msg); // 调用工具类的静态方法
	}

	function hasAnyRole(u, roles) { // 全局角色判断函数
		return PersonalCenterUtils.hasAnyRole(u, roles); // 调用工具类的静态方法
	}

	function visibleFeatures(u) { // 全局获取可见功能函数
		return PersonalCenterUtils.visibleFeatures(u); // 调用工具类的静态方法
	}

	// ==================== 全局API暴露 ====================
	window.openPersonalCenter = () => openPanel(); // 暴露打开个人中心的全局方法
	window.refreshPersonalCenterTrigger = () => buildOrUpdateTrigger(); // 暴露刷新触发器的全局方法
	window.getUserContext = () => ({ ...userContext }); // 暴露获取用户上下文的全局方法，返回用户上下文的副本
	window._pcDebug = { // 暴露调试对象到全局，包含各种内部方法和对象供调试使用
		openPanel, // 打开面板方法
		closePanel, // 关闭面板方法
		buildOrUpdateTrigger, // 构建或更新触发器方法
		setUserContext: window.setUserContext, // 设置用户上下文方法
		getUserContext: window.getUserContext, // 获取用户上下文方法
		dataManager, // 数据管理器对象
		utils: PersonalCenterUtils // 工具类对象
	};

})(); // 立即执行函数结束，完成个人中心模块的初始化
