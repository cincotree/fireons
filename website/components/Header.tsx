'use client';

import Link from 'next/link';
import { useState } from 'react';
import { appRoutes } from '@/lib/config';

export default function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <header className="bg-white/80 backdrop-blur-lg border-b border-slate-200/80 sticky top-0 z-50">
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-18">
          {/* Logo */}
          <div className="flex-shrink-0 py-4">
            <Link href="/" className="flex items-center gap-1 group">
              <svg viewBox="0 0 24 24" className="h-7 w-7 flex-shrink-0" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <linearGradient id="logoFlameGrad" x1="0" y1="1" x2="0" y2="0">
                    <stop offset="0" stopColor="#0f172a" />
                    <stop offset="0.55" stopColor="#0891b2" />
                    <stop offset="1" stopColor="#67e8f9" />
                  </linearGradient>
                </defs>
                <polygon points="12,2 16,7 14,10 18,14 15,19 12,22 9,19 6,14 10,10 8,7" fill="url(#logoFlameGrad)" />
              </svg>
              <span className="text-2xl font-bold bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent group-hover:from-cyan-600 group-hover:to-cyan-700 transition-all">
                Fireons
              </span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-1">
            <Link href="/about" className="text-slate-600 hover:text-slate-900 px-4 py-2 rounded-lg hover:bg-slate-50 transition-all font-medium">
              About FIRE
            </Link>
            <Link href="/features" className="text-slate-600 hover:text-slate-900 px-4 py-2 rounded-lg hover:bg-slate-50 transition-all font-medium">
              Features
            </Link>
            <Link href="/for-professionals" className="text-slate-600 hover:text-slate-900 px-4 py-2 rounded-lg hover:bg-slate-50 transition-all font-medium">
              For Professionals
            </Link>
            <Link href="/privacy" className="text-slate-600 hover:text-slate-900 px-4 py-2 rounded-lg hover:bg-slate-50 transition-all font-medium">
              Privacy
            </Link>
          </div>

          {/* CTA Buttons */}
          <div className="hidden md:flex items-center space-x-3">
            <Link
              href={appRoutes.waitlist}
              className="bg-cyan-600 text-white px-6 py-2.5 rounded-lg hover:bg-cyan-700 transition-all font-medium shadow-md hover:shadow-lg"
            >
              Join Waitlist
            </Link>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="text-gray-700 hover:text-blue-800 focus:outline-none"
            >
              <svg
                className="h-6 w-6"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                {isMenuOpen ? (
                  <path d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden pb-4 pt-2">
            <div className="flex flex-col space-y-2">
              <Link href="/about" className="text-slate-600 hover:text-slate-900 px-4 py-2 rounded-lg hover:bg-slate-50 transition-all font-medium">
                About FIRE
              </Link>
              <Link href="/features" className="text-slate-600 hover:text-slate-900 px-4 py-2 rounded-lg hover:bg-slate-50 transition-all font-medium">
                Features
              </Link>
              <Link href="/for-professionals" className="text-slate-600 hover:text-slate-900 px-4 py-2 rounded-lg hover:bg-slate-50 transition-all font-medium">
                For Professionals
              </Link>
              <Link href="/privacy" className="text-slate-600 hover:text-slate-900 px-4 py-2 rounded-lg hover:bg-slate-50 transition-all font-medium">
                Privacy
              </Link>
              <div className="pt-3 border-t border-slate-200 flex flex-col space-y-2 mt-2">
                <Link
                  href={appRoutes.waitlist}
                  className="bg-cyan-600 text-white px-4 py-2.5 rounded-lg hover:bg-cyan-700 transition-all font-medium text-center shadow-md"
                >
                  Join Waitlist
                </Link>
              </div>
            </div>
          </div>
        )}
      </nav>
    </header>
  );
}
