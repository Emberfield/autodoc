/**
 * Type definitions for user-related entities
 */

// Base user interface
export interface User {
  id: string;
  email: string;
  name: string;
  createdAt: Date;
  updatedAt: Date;
  isActive: boolean;
  profile?: UserProfile;
}

// User profile with additional details
export interface UserProfile {
  avatar?: string;
  bio?: string;
  location?: string;
  website?: string;
  twitter?: string;
  github?: string;
}

// Request types for user operations
export interface CreateUserRequest {
  email: string;
  name: string;
  password: string;
  profile?: Partial<UserProfile>;
}

export interface UpdateUserRequest {
  name?: string;
  email?: string;
  isActive?: boolean;
  profile?: Partial<UserProfile>;
}

// Response types
export interface UserResponse {
  user: User;
  token?: string;
}

export interface UsersListResponse {
  users: User[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

// Generic API response wrapper
export type ApiResponse<T> = {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
};

// User role enumeration
export enum UserRole {
  ADMIN = 'admin',
  USER = 'user',
  MODERATOR = 'moderator',
  GUEST = 'guest'
}

// Status type for user accounts
export type UserStatus = 'active' | 'inactive' | 'suspended' | 'pending';

// Utility type for user creation
export type CreateUser = Omit<User, 'id' | 'createdAt' | 'updatedAt'>;

// Generic filter type for user queries
export interface UserFilter {
  email?: string;
  name?: string;
  isActive?: boolean;
  role?: UserRole;
  status?: UserStatus;
  createdAfter?: Date;
  createdBefore?: Date;
}

// Pagination parameters
export interface PaginationParams {
  page?: number;
  limit?: number;
  sortBy?: keyof User;
  sortOrder?: 'asc' | 'desc';
}