

const Unavailable = () => {
  return (
    <section className="hero is-fullheight-with-navbar">
      <div className="hero-body is-flex is-justify-content-center">
        <div className="card" style={{ width: "800px", padding: "20px", height: "400px" }}>
          <div className="card-content">
            <div className="content has-text-centered">
              <h1 className="title is-size-2">Page Not Found</h1>
              <p className="subtitle is-size-4">
                Sorry, the page you are looking for is under construction.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Unavailable;


