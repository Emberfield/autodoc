/**
 * REST API controller for user operations
 * Handles HTTP requests and responses
 */

import express, { Request, Response, NextFunction } from 'express';
import { UserService } from '../user.service';
import { CreateUserRequest, UpdateUserRequest } from '../types/user.types';
import { ValidationError } from '../errors/validation.error';

export class UserController {
  private userService: UserService;

  constructor(userService: UserService) {
    this.userService = userService;
  }

  /**
   * GET /api/users/:id
   * Retrieves a user by ID
   */
  async getUser(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
      const { id } = req.params;
      const user = await this.userService.getUserById(id);
      
      if (!user) {
        res.status(404).json({ error: 'User not found' });
        return;
      }

      res.json(user);
    } catch (error) {
      next(error);
    }
  }

  /**
   * POST /api/users
   * Creates a new user
   */
  async createUser(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
      const createRequest: CreateUserRequest = req.body;
      const user = await this.userService.createUser(createRequest);
      
      res.status(201).json(user);
    } catch (error) {
      if (error instanceof ValidationError) {
        res.status(400).json({ error: error.message });
        return;
      }
      next(error);
    }
  }

  /**
   * PUT /api/users/:id
   * Updates an existing user
   */
  async updateUser(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
      const { id } = req.params;
      const updateRequest: UpdateUserRequest = req.body;
      
      const user = await this.userService.updateUser(id, updateRequest);
      res.json(user);
    } catch (error) {
      if (error instanceof ValidationError) {
        res.status(400).json({ error: error.message });
        return;
      }
      next(error);
    }
  }

  /**
   * DELETE /api/users/:id
   * Deletes a user
   */
  async deleteUser(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
      const { id } = req.params;
      await this.userService.deleteUser(id);
      
      res.status(204).send();
    } catch (error) {
      next(error);
    }
  }
}

/**
 * Creates Express router with user routes
 */
export function createUserRouter(userService: UserService): express.Router {
  const router = express.Router();
  const controller = new UserController(userService);

  router.get('/users/:id', controller.getUser.bind(controller));
  router.post('/users', controller.createUser.bind(controller));
  router.put('/users/:id', controller.updateUser.bind(controller));
  router.delete('/users/:id', controller.deleteUser.bind(controller));

  return router;
}