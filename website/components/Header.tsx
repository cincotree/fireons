'use client';

import Link from 'next/link';
import { useState } from 'react';
import { appRoutes } from '@/lib/config';

export default function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <header className="bg-white shadow-sm sticky top-0 z-50">
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex-shrink-0">
            <Link href="/" className="flex items-center">
              <span className="text-2xl font-bold text-slate-900">
                Fireons
              </span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8">
            <Link href="/about" className="text-slate-600 hover:text-slate-900 transition-colors">
              About FIRE
            </Link>
            <Link href="/features" className="text-slate-600 hover:text-slate-900 transition-colors">
              Features
            </Link>
            <Link href="/for-professionals" className="text-slate-600 hover:text-slate-900 transition-colors">
              For Professionals
            </Link>
            <Link href="/privacy" className="text-slate-600 hover:text-slate-900 transition-colors">
              Privacy
            </Link>
          </div>

          {/* CTA Buttons */}
          <div className="hidden md:flex items-center space-x-4">
            <a
              href={appRoutes.login}
              className="text-slate-700 hover:text-slate-900 font-medium transition-colors"
            >
              Login
            </a>
            <a
              href={appRoutes.register}
              className="bg-slate-900 text-white px-5 py-2.5 rounded-md hover:bg-slate-800 transition-colors font-medium"
            >
              Get Started
            </a>
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
          <div className="md:hidden pb-4">
            <div className="flex flex-col space-y-3">
              <Link href="/about" className="text-slate-600 hover:text-slate-900 transition-colors">
                About FIRE
              </Link>
              <Link href="/features" className="text-slate-600 hover:text-slate-900 transition-colors">
                Features
              </Link>
              <Link href="/for-professionals" className="text-slate-600 hover:text-slate-900 transition-colors">
                For Professionals
              </Link>
              <Link href="/privacy" className="text-slate-600 hover:text-slate-900 transition-colors">
                Privacy
              </Link>
              <div className="pt-3 border-t border-gray-200 flex flex-col space-y-3">
                <a
                  href={appRoutes.login}
                  className="text-slate-700 hover:text-slate-900 font-medium transition-colors"
                >
                  Login
                </a>
                <a
                  href={appRoutes.register}
                  className="bg-slate-900 text-white px-4 py-2 rounded-md hover:bg-slate-800 transition-colors font-medium text-center"
                >
                  Get Started
                </a>
              </div>
            </div>
          </div>
        )}
      </nav>
    </header>
  );
}
