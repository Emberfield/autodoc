/**
 * Utility functions for async operations
 * Provides helper functions for Promise handling
 */

// Generic retry function with exponential backoff
export async function retry<T>(
  fn: () => Promise<T>,
  maxAttempts: number = 3,
  baseDelay: number = 1000
): Promise<T> {
  let lastError: Error;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      
      if (attempt === maxAttempts) {
        throw lastError;
      }

      const delay = baseDelay * Math.pow(2, attempt - 1);
      await sleep(delay);
    }
  }

  throw lastError!;
}

// Sleep utility
export const sleep = (ms: number): Promise<void> => 
  new Promise(resolve => setTimeout(resolve, ms));

// Timeout wrapper for promises
export function withTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T> {
  const timeoutPromise = new Promise<never>((_, reject) => {
    setTimeout(() => reject(new Error('Operation timed out')), timeoutMs);
  });

  return Promise.race([promise, timeoutPromise]);
}

// Batch process items with concurrency limit
export async function batchProcess<T, R>(
  items: T[],
  processor: (item: T) => Promise<R>,
  concurrency: number = 5
): Promise<R[]> {
  const results: R[] = [];
  
  for (let i = 0; i < items.length; i += concurrency) {
    const batch = items.slice(i, i + concurrency);
    const batchResults = await Promise.all(
      batch.map(item => processor(item))
    );
    results.push(...batchResults);
  }

  return results;
}

// Debounce function for async operations
export function debounce<Args extends any[]>(
  fn: (...args: Args) => Promise<void>,
  delay: number
): (...args: Args) => void {
  let timeoutId: NodeJS.Timeout;

  return (...args: Args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

// Throttle function for async operations
export function throttle<Args extends any[]>(
  fn: (...args: Args) => Promise<void>,
  limit: number
): (...args: Args) => Promise<void> {
  let inThrottle: boolean;

  return async (...args: Args) => {
    if (!inThrottle) {
      await fn(...args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}