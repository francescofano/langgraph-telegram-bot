import { useState, useEffect } from 'react';
import Head from 'next/head';
import useSWR from 'swr';
import UserSelector from '../components/UserSelector';
import MemoryList from '../components/MemoryList';

// Fetcher function for SWR
const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function Home() {
  const [selectedUser, setSelectedUser] = useState<string | null>(null);

  // Fetch users
  const { data: users, error: usersError, isLoading: usersLoading } = useSWR('/api/users', fetcher);

  // Fetch memories for selected user
  const { data: memories, error: memoriesError, isLoading: memoriesLoading } = useSWR(
    selectedUser ? `/api/memories/${selectedUser}` : null,
    fetcher
  );

  // Auto-select first user if none selected
  useEffect(() => {
    if (Array.isArray(users) && users.length > 0 && !selectedUser) {
      setSelectedUser(users[0].user_id);
    }
  }, [users, selectedUser]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Head>
        <title>LangGraph Telegram Bot - Memory Dashboard</title>
        <meta name="description" content="View user memories from the LangGraph Telegram Bot" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-center mb-8 text-gray-900 dark:text-white">
          LangGraph Telegram Bot - Memory Dashboard
        </h1>

        <div className="max-w-4xl mx-auto">
          <div className="bg-white dark:bg-gray-800 shadow-md rounded-lg p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-white">User Memories</h2>
            
            {usersError ? (
              <div className="p-4 bg-red-100 text-red-700 rounded-md mb-4">
                Error loading users: {usersError.message}
              </div>
            ) : (
              <UserSelector
                users={Array.isArray(users) ? users : []}
                selectedUser={selectedUser}
                onSelectUser={setSelectedUser}
                isLoading={usersLoading}
              />
            )}
          </div>

          <div className="bg-white dark:bg-gray-800 shadow-md rounded-lg p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-800 dark:text-white">
                {selectedUser ? `Memories for ${selectedUser}` : 'Select a user to view memories'}
              </h2>
              
              {selectedUser && (
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {memories?.length || 0} memories found
                </div>
              )}
            </div>

            {memoriesError ? (
              <div className="p-4 bg-red-100 text-red-700 rounded-md">
                Error loading memories: {memoriesError.message}
              </div>
            ) : (
              <MemoryList
                memories={Array.isArray(memories) ? memories : []}
                isLoading={!!memoriesLoading || !!(selectedUser && !memories)}
              />
            )}
          </div>
        </div>
      </main>

      <footer className="py-6 text-center text-gray-500 dark:text-gray-400 text-sm">
        <p>LangGraph Telegram Bot Dashboard &copy; {new Date().getFullYear()}</p>
      </footer>
    </div>
  );
}
