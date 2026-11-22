import { Metadata } from 'next';
import GetStartedQuestionnaire from '@/components/GetStartedQuestionnaire';

export const metadata: Metadata = {
  title: 'Get Started - Fireons',
  description: 'Answer a few quick questions and get pointed to the right FIRE calculator for your situation.',
};

export default function GetStartedPage() {
  return (
    <div className="bg-white">
      {/* Hero */}
      <section className="bg-cyan-600 text-white py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold mb-6">Let&apos;s Find Your Starting Point</h1>
          <p className="text-xl text-blue-100">
            Answer a few quick questions and we&apos;ll point you to the right calculator — entirely in your browser,
            nothing is sent anywhere.
          </p>
        </div>
      </section>

      {/* Questionnaire */}
      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <GetStartedQuestionnaire />
      </section>
    </div>
  );
}
