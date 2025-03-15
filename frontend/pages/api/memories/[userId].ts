import { NextApiRequest, NextApiResponse } from 'next';
import prisma from '../../../lib/prisma';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ message: 'Method not allowed' });
  }

  const { userId } = req.query;

  if (!userId || Array.isArray(userId)) {
    return res.status(400).json({ message: 'Invalid user ID' });
  }

  try {
    // Get memories for the specified user
    const result = await prisma.store.findMany({
      where: {
        prefix: userId,
      },
      orderBy: {
        updated_at: 'desc',
      },
    });

    // Make sure we're returning an array and handle potential null/undefined values
    const formattedMemories = Array.isArray(result) 
      ? result.map(memory => ({
          key: memory?.key || 'unknown',
          content: memory?.value?.content || 'No content',
          createdAt: memory?.created_at || new Date(),
          updatedAt: memory?.updated_at || new Date(),
        }))
      : [];

    // Log the result for debugging
    console.log('Memories result type:', typeof result);
    console.log('Memories result is array:', Array.isArray(result));
    console.log('Memories result length:', result ? (Array.isArray(result) ? result.length : 'not an array') : 'null/undefined');
    console.log('Formatted memories count:', formattedMemories.length);

    return res.status(200).json(formattedMemories);
  } catch (error) {
    console.error('Error fetching memories:', error);
    return res.status(500).json({ message: 'Internal server error' });
  }
}
