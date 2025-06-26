/**
 * GitHub API client for external integrations
 * Handles communication with GitHub REST API
 */

import axios, { AxiosInstance } from 'axios';
import { Octokit } from '@octokit/rest';

export interface GitHubRepository {
  id: number;
  name: string;
  fullName: string;
  description: string;
  url: string;
  stars: number;
  forks: number;
  language: string;
}

export interface GitHubUser {
  id: number;
  login: string;
  name: string;
  email: string;
  avatarUrl: string;
  publicRepos: number;
  followers: number;
  following: number;
}

/**
 * External GitHub API client
 * Communicates with https://api.github.com
 */
export class GitHubClient {
  private octokit: Octokit;
  private httpClient: AxiosInstance;

  constructor(token?: string) {
    this.octokit = new Octokit({
      auth: token,
      baseUrl: 'https://api.github.com'
    });

    this.httpClient = axios.create({
      baseURL: 'https://api.github.com',
      headers: {
        'Authorization': token ? `Bearer ${token}` : undefined,
        'Accept': 'application/vnd.github.v3+json'
      }
    });
  }

  /**
   * Fetches user information from GitHub API
   * External call to api.github.com
   */
  async getUser(username: string): Promise<GitHubUser> {
    const response = await this.octokit.rest.users.getByUsername({
      username
    });

    return {
      id: response.data.id,
      login: response.data.login,
      name: response.data.name || '',
      email: response.data.email || '',
      avatarUrl: response.data.avatar_url,
      publicRepos: response.data.public_repos,
      followers: response.data.followers,
      following: response.data.following
    };
  }

  /**
   * Fetches repositories for a user
   * Makes external HTTP call to GitHub
   */
  async getUserRepositories(username: string): Promise<GitHubRepository[]> {
    const response = await this.httpClient.get(`/users/${username}/repos`);
    
    return response.data.map((repo: any) => ({
      id: repo.id,
      name: repo.name,
      fullName: repo.full_name,
      description: repo.description || '',
      url: repo.html_url,
      stars: repo.stargazers_count,
      forks: repo.forks_count,
      language: repo.language || 'Unknown'
    }));
  }

  /**
   * Creates a new repository via GitHub API
   * External API call
   */
  async createRepository(name: string, description?: string): Promise<GitHubRepository> {
    const response = await this.octokit.rest.repos.createForAuthenticatedUser({
      name,
      description,
      private: false
    });

    return {
      id: response.data.id,
      name: response.data.name,
      fullName: response.data.full_name,
      description: response.data.description || '',
      url: response.data.html_url,
      stars: response.data.stargazers_count,
      forks: response.data.forks_count,
      language: response.data.language || 'Unknown'
    };
  }

  /**
   * Searches repositories on GitHub
   * External search API call
   */
  async searchRepositories(query: string, language?: string): Promise<GitHubRepository[]> {
    const searchQuery = language ? `${query} language:${language}` : query;
    
    const response = await this.octokit.rest.search.repos({
      q: searchQuery,
      sort: 'stars',
      order: 'desc',
      per_page: 50
    });

    return response.data.items.map(repo => ({
      id: repo.id,
      name: repo.name,
      fullName: repo.full_name,
      description: repo.description || '',
      url: repo.html_url,
      stars: repo.stargazers_count,
      forks: repo.forks_count,
      language: repo.language || 'Unknown'
    }));
  }
}

/**
 * Factory function for creating GitHub client
 */
export function createGitHubClient(token?: string): GitHubClient {
  return new GitHubClient(token);
}