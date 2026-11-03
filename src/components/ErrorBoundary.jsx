import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary a capturé une erreur :', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="rounded-lg border border-red-300 dark:border-red-800 bg-red-50 dark:bg-red-950/40 p-6 my-4 text-center">
          <p className="text-sm font-semibold text-red-700 dark:text-red-300 mb-2">
            ⚠️ Une erreur inattendue est survenue lors de l'affichage de cette section.
          </p>
          <p className="text-xs text-red-600 dark:text-red-400 font-mono mb-4">
            {this.state.error?.message || 'Erreur de rendu'}
          </p>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false, error: null })}
            className="text-xs px-3 py-1.5 rounded-md bg-red-600 hover:bg-red-500 text-white font-medium transition-colors"
          >
            Réessayer l'affichage
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

