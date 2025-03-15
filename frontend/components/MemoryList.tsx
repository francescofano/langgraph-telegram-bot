import React from 'react';

interface Memory {
  key: string;
  content: string;
  createdAt: string;
  updatedAt: string;
}

interface MemoryListProps {
  memories: Memory[];
  isLoading: boolean;
}

const MemoryList: React.FC<MemoryListProps> = ({ memories, isLoading }) => {
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (!memories || memories.length === 0) {
    return (
      <div className="text-center p-8 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <p className="text-gray-500 dark:text-gray-400">No memories found for this user.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {memories.map((memory) => (
        <div key={memory.key} className="card border border-gray-200 dark:border-gray-700">
          <div className="flex justify-between items-start mb-2">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white truncate">
              {memory.key}
            </h3>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {new Date(memory.updatedAt).toLocaleString()}
            </div>
          </div>
          <p className="text-gray-700 dark:text-gray-300">{memory.content}</p>
          <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            Created: {new Date(memory.createdAt).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
};

export default MemoryList;
