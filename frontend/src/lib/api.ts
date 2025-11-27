import axios from 'axios'

// Use relative URL to leverage Vite proxy (avoids CORS issues in development)
// In production, this will be set via VITE_API_URL environment variable
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add token to requests if available
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 errors (unauthorized)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Types matching backend Pydantic models
export interface EventResponse {
  id: number
  delivery_id: string | null
  event_type: string
  repo: string | null
  ref: string | null
  after_sha: string | null
  created_at: string
  latest_review_status: string | null
  latest_review_id: number | null
}

export interface ReviewResponse {
  id: number
  event_id: number
  status: string
  started_at: string | null
  finished_at: string | null
  summary_json: string | null
}

export interface FindingResponse {
  id: number
  review_id: number
  file_path: string | null
  severity: string
  title: string
  rationale: string | null
  start_line: number | null
  end_line: number | null
  patch: string | null
  tool: string | null
}

export interface EventDetailResponse {
  event: EventResponse
  reviews: ReviewResponse[]
}

export interface ReviewDetailResponse {
  review: ReviewResponse
  event: EventResponse
  findings: FindingResponse[]
  findings_by_file: Record<string, FindingResponse[]>
}

export interface PaginatedEventsResponse {
  events: EventResponse[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface HealthResponse {
  ok: boolean
  env: string
}

export interface EnqueueResponse {
  success: boolean
  message: string
  event_id: number
}

export interface GetEventsParams {
  page?: number
  pageSize?: number
  repo?: string
  eventType?: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: {
    id: number
    email: string
    name: string
  }
}

export interface UserResponse {
  id: number
  email: string
  name: string
  created_at: string
}

export interface RepositoryResponse {
  id: number
  user_id: number
  repo_full_name: string
  webhook_secret: string
  webhook_url: string
  is_active: boolean
  created_at: string
}

export interface CreateRepositoryRequest {
  repo_full_name: string
  github_token?: string
}

export const api = {
  // Health check
  async getHealth(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/health')
    return response.data
  },

  // Events
  async getEvents(params: GetEventsParams = {}): Promise<PaginatedEventsResponse> {
    const { page = 1, pageSize = 50, repo, eventType } = params
    const response = await apiClient.get<PaginatedEventsResponse>('/events', {
      params: {
        page,
        page_size: pageSize,
        repo,
        event_type: eventType,
      },
    })
    return response.data
  },

  async getEvent(eventId: number): Promise<EventDetailResponse> {
    const response = await apiClient.get<EventDetailResponse>(`/events/${eventId}`)
    return response.data
  },

  async enqueueEvent(eventId: number): Promise<EnqueueResponse> {
    const response = await apiClient.post<EnqueueResponse>(`/events/${eventId}/enqueue`)
    return response.data
  },

  // Reviews
  async getReview(reviewId: number): Promise<ReviewDetailResponse> {
    const response = await apiClient.get<ReviewDetailResponse>(`/reviews/${reviewId}`)
    return response.data
  },

  async getReviewFindings(reviewId: number): Promise<FindingResponse[]> {
    const response = await apiClient.get<FindingResponse[]>(`/reviews/${reviewId}/findings`)
    return response.data
  },

  // Authentication
  async signup(email: string, password: string, name: string): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/signup', {
      email,
      password,
      name,
    })
    return response.data
  },

  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/login', {
      email,
      password,
    })
    return response.data
  },

  async getCurrentUser(token?: string): Promise<UserResponse> {
    const headers = token ? { Authorization: `Bearer ${token}` } : {}
    const response = await apiClient.get<UserResponse>('/auth/me', { headers })
    return response.data
  },

  // Repositories
  async getRepositories(): Promise<RepositoryResponse[]> {
    const response = await apiClient.get<RepositoryResponse[]>('/repositories')
    return response.data
  },

  async createRepository(request: CreateRepositoryRequest): Promise<RepositoryResponse> {
    const response = await apiClient.post<RepositoryResponse>('/repositories', request)
    return response.data
  },

  async getRepository(repoId: number): Promise<RepositoryResponse> {
    const response = await apiClient.get<RepositoryResponse>(`/repositories/${repoId}`)
    return response.data
  },

  async disconnectRepository(repoId: number): Promise<{ message: string }> {
    const response = await apiClient.delete(`/repositories/${repoId}`)
    return response.data
  },
}

