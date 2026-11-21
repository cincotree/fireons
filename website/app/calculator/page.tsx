'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { appRoutes } from '@/lib/config';

export default function CalculatorRedirect() {
  useEffect(() => {
    window.location.replace(appRoutes.retirementCalculator);
  }, []);

  return (
    <div className="min-h-[50vh] flex items-center justify-center px-4 text-center">
      <p className="text-slate-600">
        This calculator has moved.{' '}
        <Link href={appRoutes.retirementCalculator} className="text-cyan-700 font-semibold hover:underline">
          Continue to the Retirement Calculator →
        </Link>
      </p>
    </div>
  );
}
