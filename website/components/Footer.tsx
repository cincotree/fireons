import Link from 'next/link';
import { appRoutes } from '@/lib/config';

export default function Footer() {
  return (
    <footer className="bg-slate-900 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-1">
            <h3 className="text-2xl font-bold mb-4">
              Fireons
            </h3>
            <p className="text-gray-400 text-sm">
              Community for achieving financial independence.
            </p>
          </div>

          {/* About */}
          <div>
            <h4 className="font-semibold mb-4">About</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/about" className="text-gray-400 hover:text-white transition-colors">
                  What is FIRE?
                </Link>
              </li>
              <li>
                <Link href="/features" className="text-gray-400 hover:text-white transition-colors">
                  Features
                </Link>
              </li>
              <li>
                <Link href="/privacy" className="text-gray-400 hover:text-white transition-colors">
                  Privacy Policy
                </Link>
              </li>
            </ul>
          </div>

          {/* For Users */}
          <div>
            <h4 className="font-semibold mb-4">For Fireons</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <a href={appRoutes.register} className="text-gray-400 hover:text-white transition-colors">
                  Join Community
                </a>
              </li>
              <li>
                <a href={appRoutes.login} className="text-gray-400 hover:text-white transition-colors">
                  Login
                </a>
              </li>
            </ul>
          </div>

          {/* For Professionals */}
          <div>
            <h4 className="font-semibold mb-4">For Professionals</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/for-professionals" className="text-gray-400 hover:text-white transition-colors">
                  Learn More
                </Link>
              </li>
              <li>
                <a href={appRoutes.registerProfessional} className="text-gray-400 hover:text-white transition-colors">
                  Join as Advisor
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="border-t border-gray-800 mt-8 pt-8 text-center text-sm text-gray-400">
          <p>&copy; {new Date().getFullYear()} Fireons. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
