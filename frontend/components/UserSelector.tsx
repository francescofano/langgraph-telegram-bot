import React from 'react';

interface User {
  user_id: string;
}

interface UserSelectorProps {
  users: User[];
  selectedUser: string | null;
  onSelectUser: (userId: string) => void;
  isLoading: boolean;
}

const UserSelector: React.FC<UserSelectorProps> = ({
  users,
  selectedUser,
  onSelectUser,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div className="w-full p-4 bg-black-100 dark:bg-gray-800 rounded-lg animate-pulse">
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded"></div>
      </div>
    );
  }

  if (!users || users.length === 0) {
    return (
      <div className="w-full p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
        <p className="text-gray-500 dark:text-gray-400">No users found with memories.</p>
      </div>
    );
  }

  return (
    <div className="w-full">
      <label htmlFor="user-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        Select User
      </label>
      <select
        id="user-select"
        className="select w-full"
        value={selectedUser || ''}
        onChange={(e) => onSelectUser(e.target.value)}
      >
        <option value="" disabled>
          Select a user
        </option>
        {users.map((user) => (
          <option key={user.user_id} value={user.user_id}>
            {user.user_id}
          </option>
        ))}
      </select>
    </div>
  );
};

export default UserSelector;
