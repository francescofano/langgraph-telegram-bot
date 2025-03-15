import { NextApiRequest, NextApiResponse } from 'next';
import prisma from '../../lib/prisma';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ message: 'Method not allowed' });
  }

  try {
    // Get distinct prefixes (user_ids) from the store table
    const result = await prisma.store.findMany({
      select: {
        prefix: true,
      },
      distinct: ['prefix'],
      orderBy: {
        prefix: 'asc',
      },
    });

    // Make sure we're returning an array and handle potential null/undefined values
    const formattedUsers = Array.isArray(result) 
      ? result.map(user => ({ user_id: user?.prefix || 'unknown' }))
      : [];

    // Log the result for debugging
    console.log('Users result type:', typeof result);
    console.log('Users result is array:', Array.isArray(result));
    console.log('Users result length:', result ? (Array.isArray(result) ? result.length : 'not an array') : 'null/undefined');
    console.log('Formatted users:', formattedUsers);

    return res.status(200).json(formattedUsers);
  } catch (error) {
    console.error('Error fetching users:', error);
    return res.status(500).json({ message: 'Internal server error' });
  }
}
