import { useState, useEffect } from 'react'
import { supabase } from '../utils/supabase'
import { CheckCircle2, Circle, ListTodo, Plus, Trash2, ArrowLeft } from 'lucide-react'
import { Link } from 'react-router'

interface Todo {
  id: string
  name: string
  is_completed?: boolean
}

export default function TodoDemo() {
  const [todos, setTodos] = useState<Todo[]>([])
  const [newTodoName, setNewTodoName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function getTodos() {
      try {
        setLoading(true)
        const { data: todosData, error: fetchError } = await supabase
          .from('todos')
          .select()

        if (fetchError) {
          throw fetchError
        }

        if (todosData) {
          setTodos(todosData)
        }
      } catch (err: any) {
        setError(err.message || 'Failed to fetch todos')
      } finally {
        setLoading(false)
      }
    }

    getTodos()
  }, [])

  const handleAddTodo = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTodoName.trim()) return

    try {
      const { data, error: insertError } = await supabase
        .from('todos')
        .insert([{ name: newTodoName.trim() }])
        .select()

      if (insertError) {
        throw insertError
      }

      if (data) {
        setTodos((prev) => [...prev, ...data])
        setNewTodoName('')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to add todo')
    }
  }

  const handleDeleteTodo = async (id: string) => {
    try {
      const { error: deleteError } = await supabase
        .from('todos')
        .delete()
        .eq('id', id)

      if (deleteError) {
        throw deleteError
      }

      setTodos((prev) => prev.filter((todo) => todo.id !== id))
    } catch (err: any) {
      setError(err.message || 'Failed to delete todo')
    }
  }

  return (
    <div className="min-h-screen w-full bg-black text-[#e0e0e0] font-sans flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute top-1/4 left-1/4 w-[400px] h-[400px] bg-[#c8956c]/10 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[300px] h-[300px] bg-amber-500/5 rounded-full blur-[80px] pointer-events-none" />

      {/* Main Container */}
      <div className="w-full max-w-xl liquid-glass rounded-2xl border border-white/10 p-8 shadow-2xl relative z-10">
        <div className="flex items-center justify-between mb-8">
          <Link 
            to="/research" 
            className="flex items-center gap-2 text-sm text-[#999] hover:text-[#c8956c] transition-colors cursor-pointer group"
          >
            <ArrowLeft className="w-4 h-4 transform group-hover:-translate-x-1 transition-transform" />
            Back to Dashboard
          </Link>
          <div className="flex items-center gap-2 bg-white/5 border border-white/5 rounded-full px-3 py-1 text-xs text-[#999]">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            Supabase Live
          </div>
        </div>

        <div className="flex items-center gap-3 mb-6">
          <ListTodo className="w-8 h-8 text-[#c8956c]" />
          <h1 className="text-2xl font-bold tracking-tight text-white">Todo Query Demo</h1>
        </div>
        
        <p className="text-sm text-[#999] mb-8 leading-relaxed">
          This demo queries data from the <code>todos</code> table in your Supabase database using the newly initialized Supabase client in <code>frontend/src/utils/supabase.ts</code>.
        </p>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Add Todo Form */}
        <form onSubmit={handleAddTodo} className="flex gap-2 mb-8">
          <input
            type="text"
            value={newTodoName}
            onChange={(e) => setNewTodoName(e.target.value)}
            placeholder="Add a new task..."
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-[#c8956c]/50 transition-colors text-white placeholder-white/30"
          />
          <button
            type="submit"
            className="bg-[#c8956c] hover:bg-[#b0805c] text-black font-semibold text-sm rounded-lg px-4 py-2.5 flex items-center justify-center gap-2 cursor-pointer transition-all hover:scale-[1.02] active:scale-[0.98] border-none"
          >
            <Plus className="w-4 h-4 stroke-[3]" />
            Add
          </button>
        </form>

        {/* Todo List */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3 text-[#999]">
            <div className="w-6 h-6 border-2 border-white/10 border-t-[#c8956c] rounded-full animate-spin" />
            <span className="text-xs">Fetching from Supabase...</span>
          </div>
        ) : todos.length === 0 ? (
          <div className="text-center py-12 text-[#999] border border-dashed border-white/5 rounded-xl">
            <p className="text-sm mb-1">No todos found</p>
            <p className="text-xs text-white/30">Create one above to check persistence</p>
          </div>
        ) : (
          <div className="flex flex-col gap-2.5 max-h-[300px] overflow-y-auto pr-1 custom-scrollbar">
            {todos.map((todo) => (
              <div 
                key={todo.id}
                className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/5 hover:border-white/10 hover:bg-white/10 transition-all group"
              >
                <div className="flex items-center gap-3">
                  {todo.is_completed ? (
                    <CheckCircle2 className="w-5 h-5 text-green-500 shrink-0" />
                  ) : (
                    <Circle className="w-5 h-5 text-[#999] shrink-0" />
                  )}
                  <span className={`text-sm ${todo.is_completed ? 'line-through text-white/30' : 'text-[#e0e0e0]'}`}>
                    {todo.name}
                  </span>
                </div>
                <button
                  onClick={() => handleDeleteTodo(todo.id)}
                  className="text-white/20 hover:text-red-400 p-1.5 rounded-lg hover:bg-white/5 transition-colors cursor-pointer opacity-0 group-hover:opacity-100 focus:opacity-100 border-none bg-transparent"
                  aria-label={`Delete task: ${todo.name}`}
                  title="Delete task"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
