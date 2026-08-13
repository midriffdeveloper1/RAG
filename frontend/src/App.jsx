import Header from "./components/layout/Header.jsx";
import Footer from "./components/layout/Footer.jsx";
import Home from "./pages/Home.jsx";

export default function App() {
  return (
    <div className="app-shell">
      <Header />
      <main className="app-main">
        <Home />
      </main>
      <Footer />
    </div>
  );
}
