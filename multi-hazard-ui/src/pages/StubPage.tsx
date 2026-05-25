import NavBar from '../components/NavBar';

export default function StubPage({ title }: { title: string }) {
  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />
      <div className="flex-1 flex items-center justify-center text-center p-12">
        <div>
          <h1 className="text-3xl font-bold text-hub-800 mb-3">{title}</h1>
          <p className="text-gray-500">This section is coming soon.</p>
        </div>
      </div>
    </div>
  );
}
