/**
 * User service for managing user operations
 * Provides CRUD operations for user entities
 */

import { User, CreateUserRequest, UpdateUserRequest } from './types/user.types';
import { DatabaseService } from './database.service';
import { Logger } from './utils/logger';
import { ValidationError } from './errors/validation.error';

export interface UserService {
  createUser(request: CreateUserRequest): Promise<User>;
  getUserById(id: string): Promise<User | null>;
  updateUser(id: string, request: UpdateUserRequest): Promise<User>;
  deleteUser(id: string): Promise<void>;
}

/**
 * Implementation of UserService interface
 * Handles all user-related business logic
 */
export class UserServiceImpl implements UserService {
  private logger: Logger;
  private database: DatabaseService;

  constructor(database: DatabaseService, logger: Logger) {
    this.database = database;
    this.logger = logger;
  }

  /**
   * Creates a new user in the system
   * @param request User creation request data
   * @returns Promise resolving to created user
   * @throws ValidationError if request data is invalid
   */
  async createUser(request: CreateUserRequest): Promise<User> {
    this.logger.info('Creating new user', { email: request.email });
    
    if (!this.validateEmail(request.email)) {
      throw new ValidationError('Invalid email format');
    }

    const existingUser = await this.database.findUserByEmail(request.email);
    if (existingUser) {
      throw new ValidationError('User with this email already exists');
    }

    const user: User = {
      id: this.generateId(),
      email: request.email,
      name: request.name,
      createdAt: new Date(),
      updatedAt: new Date(),
      isActive: true
    };

    await this.database.saveUser(user);
    this.logger.info('User created successfully', { userId: user.id });
    
    return user;
  }

  /**
   * Retrieves a user by their ID
   */
  async getUserById(id: string): Promise<User | null> {
    this.logger.debug('Fetching user by ID', { userId: id });
    return await this.database.findUserById(id);
  }

  /**
   * Updates an existing user
   */
  async updateUser(id: string, request: UpdateUserRequest): Promise<User> {
    const existingUser = await this.getUserById(id);
    if (!existingUser) {
      throw new ValidationError('User not found');
    }

    const updatedUser: User = {
      ...existingUser,
      ...request,
      updatedAt: new Date()
    };

    await this.database.saveUser(updatedUser);
    return updatedUser;
  }

  /**
   * Soft deletes a user (marks as inactive)
   */
  async deleteUser(id: string): Promise<void> {
    await this.updateUser(id, { isActive: false });
    this.logger.info('User deleted', { userId: id });
  }

  private validateEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  private generateId(): string {
    return 'user_' + Math.random().toString(36).substr(2, 9);
  }
}