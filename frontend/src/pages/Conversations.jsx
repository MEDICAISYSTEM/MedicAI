import { useState, useEffect } from "react";
import { getConversations, getConversation } from "../lib/api";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { ScrollArea } from "../components/ui/scroll-area";
import { 
  MessageSquare, 
  Search, 
  Phone,
  Clock,
  Loader2,
  Bot,
  User,
  ChevronRight,
  ArrowLeft
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";

export default function Conversations() {
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    fetchConversations();
  }, []);

  const fetchConversations = async () => {
    try {
      const response = await getConversations();
      setConversations(response.data);
    } catch (error) {
      toast.error("Error al cargar las conversaciones");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectConversation = async (conv) => {
    setLoadingMessages(true);
    try {
      const response = await getConversation(conv.id);
      setSelectedConversation(response.data);
    } catch (error) {
      toast.error("Error al cargar los mensajes");
    } finally {
      setLoadingMessages(false);
    }
  };

  const filteredConversations = conversations.filter((conv) => {
    const matchesSearch = 
      conv.patient_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      conv.patient_phone?.includes(searchTerm);
    return matchesSearch;
  });

  const getIntentBadge = (intent) => {
    switch (intent) {
      case 'urgency':
        return <Badge className="badge-error text-xs">Urgencia</Badge>;
      case 'appointment':
        return <Badge className="badge-success text-xs">Cita</Badge>;
      case 'pricing':
        return <Badge className="badge-warning text-xs">Precios</Badge>;
      default:
        return <Badge className="badge-neutral text-xs">General</Badge>;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="conversations-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
          Conversaciones
        </h1>
        <p className="text-slate-500 mt-1">Historial de chats con pacientes vía WhatsApp</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-250px)]">
        {/* Conversations List */}
        <Card className={`stat-card lg:col-span-1 ${selectedConversation ? 'hidden lg:block' : ''}`}>
          <CardHeader className="pb-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                placeholder="Buscar conversación..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 input-base"
                data-testid="search-conversations"
              />
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
              </div>
            ) : filteredConversations.length === 0 ? (
              <div className="text-center py-12 text-slate-500 px-4">
                <MessageSquare className="w-12 h-12 mx-auto mb-3 text-slate-300" />
                <p>No hay conversaciones</p>
              </div>
            ) : (
              <ScrollArea className="h-[calc(100vh-380px)]">
                <div className="divide-y divide-slate-100">
                  {filteredConversations.map((conv) => (
                    <button
                      key={conv.id}
                      onClick={() => handleSelectConversation(conv)}
                      className={`w-full p-4 text-left hover:bg-slate-50 transition-colors ${
                        selectedConversation?.id === conv.id ? 'bg-sky-50' : ''
                      }`}
                      data-testid={`conversation-${conv.id}`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-sky-100 rounded-full flex items-center justify-center flex-shrink-0">
                          <span className="text-sky-600 font-semibold text-sm">
                            {conv.patient_name?.charAt(0)?.toUpperCase() || '?'}
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <p className="font-medium text-slate-900 truncate">
                              {conv.patient_name || 'Sin nombre'}
                            </p>
                            <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
                          </div>
                          <p className="text-sm text-slate-500 flex items-center gap-1">
                            <Phone className="w-3 h-3" />
                            {conv.patient_phone}
                          </p>
                          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {conv.last_message_at 
                              ? format(parseISO(conv.last_message_at), "d MMM, HH:mm", { locale: es })
                              : 'Sin mensajes'}
                          </p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>

        {/* Messages Panel */}
        <Card className={`stat-card lg:col-span-2 ${!selectedConversation ? 'hidden lg:flex lg:items-center lg:justify-center' : ''}`}>
          {!selectedConversation ? (
            <div className="text-center text-slate-500">
              <MessageSquare className="w-16 h-16 mx-auto mb-4 text-slate-300" />
              <p className="text-lg font-medium">Selecciona una conversación</p>
              <p className="text-sm">para ver el historial de mensajes</p>
            </div>
          ) : (
            <div className="h-full flex flex-col">
              {/* Conversation Header */}
              <CardHeader className="border-b border-slate-100 flex-shrink-0">
                <div className="flex items-center gap-4">
                  <button 
                    onClick={() => setSelectedConversation(null)}
                    className="lg:hidden p-2 hover:bg-slate-100 rounded-lg"
                  >
                    <ArrowLeft className="w-5 h-5" />
                  </button>
                  <div className="w-12 h-12 bg-sky-100 rounded-full flex items-center justify-center">
                    <span className="text-sky-600 font-semibold">
                      {selectedConversation.patient_name?.charAt(0)?.toUpperCase() || '?'}
                    </span>
                  </div>
                  <div>
                    <CardTitle className="text-lg">
                      {selectedConversation.patient_name || 'Sin nombre'}
                    </CardTitle>
                    <p className="text-sm text-slate-500 flex items-center gap-1">
                      <Phone className="w-3 h-3" />
                      {selectedConversation.patient_phone}
                    </p>
                  </div>
                  <Badge className={selectedConversation.status === 'active' ? 'badge-success ml-auto' : 'badge-neutral ml-auto'}>
                    {selectedConversation.status === 'active' ? 'Activa' : 'Cerrada'}
                  </Badge>
                </div>
              </CardHeader>

              {/* Messages */}
              <CardContent className="flex-1 overflow-hidden p-0">
                {loadingMessages ? (
                  <div className="flex items-center justify-center h-full">
                    <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
                  </div>
                ) : (
                  <ScrollArea className="h-[calc(100vh-450px)] p-4">
                    <div className="space-y-4">
                      {selectedConversation.messages?.map((msg) => (
                        <div 
                          key={msg.id}
                          className={`flex ${msg.sender === 'patient' ? 'justify-start' : 'justify-end'}`}
                          data-testid={`message-${msg.id}`}
                        >
                          <div className={`max-w-[80%] ${msg.sender === 'patient' ? 'order-2' : 'order-1'}`}>
                            <div className={`flex items-end gap-2 ${msg.sender === 'patient' ? '' : 'flex-row-reverse'}`}>
                              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                                msg.sender === 'patient' ? 'bg-slate-200' : 'bg-sky-500'
                              }`}>
                                {msg.sender === 'patient' ? (
                                  <User className="w-4 h-4 text-slate-600" />
                                ) : (
                                  <Bot className="w-4 h-4 text-white" />
                                )}
                              </div>
                              <div className={`rounded-2xl px-4 py-3 ${
                                msg.sender === 'patient' 
                                  ? 'bg-slate-100 text-slate-900 rounded-bl-md' 
                                  : 'bg-sky-500 text-white rounded-br-md'
                              }`}>
                                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                              </div>
                            </div>
                            <div className={`flex items-center gap-2 mt-1 ${msg.sender === 'patient' ? 'ml-10' : 'mr-10 justify-end'}`}>
                              <span className="text-xs text-slate-400">
                                {format(parseISO(msg.timestamp), "HH:mm", { locale: es })}
                              </span>
                              {msg.intent && getIntentBadge(msg.intent)}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                )}
              </CardContent>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
