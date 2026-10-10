/**
 * API client for LAYOVER backend integration
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ApiAdventureRequest {
  start: string;
  startLat?: number;
  startLng?: number; 
  minutes: number;
  budget: number;
  buffer: number;
  mode: 'walk' | 'transit' | 'both';
  style: 'history' | 'food' | 'culture' | 'nature' | 'mixed';
  difficulty: 'easy' | 'medium' | 'challenging';
  delayMinutes?: number;
  scheduledDeparture?: string;
}

export interface ApiLocation {
  name: string;
  lat: number;
  lng: number;
}

export interface ApiMission {
  id: string;
  name: string;
  lat: number;
  lng: number;
  travelMin: number;
  visitMin: number;
  returnMin: number;
  cost: number;
  title: string;
  intro: string;
  riddle: string;
  hints: string[];
  answers: string[];
  story: string;
  activity: string;
}

export interface ApiAdventureResponse {
  id: string;
  title: string;
  source: 'ai' | 'fallback';
  usableMinutes: number;
  estimatesNote: string;
  warnings: string[];
  start: ApiLocation;
  missions: ApiMission[];
}

export interface ApiHealthResponse {
  status: string;
  llmConfigured: boolean;
  placesSourceReachable: boolean;
}

export interface ApiGeocodeResponse {
  name: string;
  lat: number;
  lng: number;
}

export interface ApiReplanRequest {
  remainingMinutes: number;
  remainingBudget: number;
  currentLat: number;
  currentLng: number;
  completedIds: string[];
}

export interface ApiAnswerRequest {
  missionId: string;
  answer: string;
}

export interface ApiAnswerResponse {
  correct: boolean;
}

export interface ApiHintRequest {
  missionId: string;
  level: number;
}

export interface ApiHintResponse {
  hint: string;
}

class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}`;
      let errorDetails;
      
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
        errorDetails = errorData;
      } catch {
        errorMessage = response.statusText || errorMessage;
      }
      
      throw new ApiError(response.status, errorMessage, errorDetails);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    
    // Network or other errors
    throw new ApiError(0, 'Network error or server unreachable', { originalError: error });
  }
}

export const api = {
  async healthCheck(): Promise<ApiHealthResponse> {
    return fetchApi<ApiHealthResponse>('/api/health');
  },

  async createAdventure(request: ApiAdventureRequest): Promise<ApiAdventureResponse> {
    return fetchApi<ApiAdventureResponse>('/api/adventures', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  async getAdventure(id: string): Promise<ApiAdventureResponse> {
    return fetchApi<ApiAdventureResponse>(`/api/adventures/${id}`);
  },

  async replanAdventure(id: string, request: ApiReplanRequest): Promise<ApiAdventureResponse> {
    return fetchApi<ApiAdventureResponse>(`/api/adventures/${id}/replan`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  async checkAnswer(adventureId: string, request: ApiAnswerRequest): Promise<ApiAnswerResponse> {
    return fetchApi<ApiAnswerResponse>(`/api/adventures/${adventureId}/answer`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  async getHint(adventureId: string, request: ApiHintRequest): Promise<ApiHintResponse> {
    return fetchApi<ApiHintResponse>(`/api/adventures/${adventureId}/hint`, {
      method: 'POST', 
      body: JSON.stringify(request),
    });
  },

  async geocode(query: string): Promise<ApiGeocodeResponse> {
    const params = new URLSearchParams({ q: query });
    return fetchApi<ApiGeocodeResponse>(`/api/geocode?${params}`);
  },
};