/**
 * API 客户端 - 统一的后端 API 调用封装
 */
class APIClient {
	/**
	 * 基础请求方法
	 */
	static async request(url, options = {}) {
		try {
			const response = await fetch(url, {
				headers: {
					'Content-Type': 'application/json',
					...options.headers
				},
				...options
			});

			const data = await response.json();

			// 处理新的统一响应格式
			if (!response.ok) {
				// 错误响应格式: { success: false, error: "...", code: "...", detail: "..." }
				throw new Error(data.error || data.detail || `HTTP ${response.status}`);
			}

			// 成功响应可能是直接数据或包装格式: { success: true, data: {...} }
			return data.data !== undefined ? data.data : data;
		} catch (error) {
			console.error(`[APIClient] Request failed: ${url}`, error);
			throw error;
		}
	}

	// ==================== 认证相关 API ====================

	/**
	 * 用户登录
	 */
	static async login(username, password) {
		return await this.request('/api/auth/login', {
			method: 'POST',
			body: JSON.stringify({ username, password })
		});
	}

	/**
	 * 用户注册
	 */
	static async register(username, password, email = null) {
		return await this.request('/api/auth/register', {
			method: 'POST',
			body: JSON.stringify({ username, password, email })
		});
	}

	/**
	 * 用户登出
	 */
	static async logout(token) {
		return await this.request('/api/auth/logout', {
			method: 'POST',
			body: JSON.stringify({ token })
		});
	}

	/**
	 * 验证 Token
	 */
	static async verifyToken(token) {
		return await this.request(`/api/auth/verify?token=${encodeURIComponent(token)}`);
	}

	// ==================== 试卷相关 API ====================

	/**
	 * 获取试卷列表
	 * @param {Object} options - 查询选项
	 * @param {string} options.level - 级别过滤 (N1, N2, N3, N4, N5)
	 * @param {string} options.year - 年份过滤
	 * @param {string} options.sort - 排序方式 (date_desc, date_asc, level)
	 */
	static async getExams(options = {}) {
		const params = new URLSearchParams();
		if (options.level) params.append('level', options.level);
		if (options.year) params.append('year', options.year);
		if (options.sort) params.append('sort', options.sort);
		
		const query = params.toString();
		const url = query ? `/api/exams?${query}` : '/api/exams';
		
		return await this.request(url);
	}

	/**
	 * 获取单个试卷
	 */
	static async getExam(examId) {
		return await this.request(`/api/exams/${examId}`);
	}

	/**
	 * 创建试卷
	 */
	static async createExam(examData) {
		return await this.request('/api/exams', {
			method: 'POST',
			body: JSON.stringify(examData)
		});
	}

	/**
	 * 删除试卷
	 */
	static async deleteExam(examId) {
		return await this.request(`/api/exams/${examId}`, {
			method: 'DELETE'
		});
	}

	// ==================== 答案相关 API ====================

	/**
	 * 提交答案
	 */
	static async submitAnswers(userId, examId, answers) {
		return await this.request('/api/answers/submit', {
			method: 'POST',
			body: JSON.stringify({
				user_id: userId,
				exam_id: examId,
				answers: answers
			})
		});
	}

	/**
	 * 获取用户答案
	 */
	static async getAnswers(userId, examId) {
		return await this.request(`/api/answers/${userId}/${examId}`);
	}

	/**
	 * 获取学习进度
	 */
	static async getProgress(userId) {
		return await this.request(`/api/progress/${userId}`);
	}

	// ==================== 统计相关 API ====================

	/**
	 * 获取用户统计
	 */
	static async getStatistics(userId) {
		return await this.request(`/api/statistics/${userId}`);
	}

	/**
	 * 获取薄弱点
	 */
	static async getWeakPoints(userId) {
		return await this.request(`/api/statistics/${userId}/weak-points`);
	}

	/**
	 * 获取学习曲线
	 */
	static async getLearningCurve(userId, days = 30) {
		return await this.request(`/api/statistics/${userId}/learning-curve?days=${days}`);
	}

	/**
	 * 获取推荐试卷
	 */
	static async getRecommendations(userId, limit = 5) {
		return await this.request(`/api/statistics/${userId}/recommendations?limit=${limit}`);
	}

	// ==================== 用户相关 API ====================

	/**
	 * 获取用户信息
	 */
	static async getUser(userId) {
		return await this.request(`/api/users/${userId}`);
	}

	/**
	 * 获取指定角色的用户列表
	 */
	static async getUsersByRole(roleId) {
		return await this.request(`/api/users/by-role/${roleId}`);
	}

	/**
	 * 获取用户权限（可见的功能和区域）
	 */
	static async getUserPermissions(userId) {
		return await this.request(`/api/users/${userId}/permissions`);
	}

	/**
	 * 获取所有角色定义
	 */
	static async getAllRoles() {
		return await this.request('/api/roles');
	}

	// ==================== 振假名相关 API ====================

	/**
	 * 添加振假名
	 */
	static async addFurigana(text) {
		return await this.request('/api/furigana/add', {
			method: 'POST',
			body: JSON.stringify({ text })
		});
	}

	/**
	 * 获取单词读音
	 */
	static async getReading(word) {
		return await this.request(`/api/furigana/reading/${encodeURIComponent(word)}`);
	}
}

// 导出到全局作用域
window.APIClient = APIClient;
