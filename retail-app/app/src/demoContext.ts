import { createContext, useContext } from 'react';

export const DemoContext = createContext<'bookshelf' | 'retail'>('bookshelf');
export const useRetail = () => useContext(DemoContext) === 'retail';
