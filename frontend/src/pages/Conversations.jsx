import { useState, useEffect } from "react";
import { getConversations, getConversation } from "../lib/api";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
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
  ArrowLeft,
  RefreshCw
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
    setLoading(true);
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
        return null;
    }
  };

  return (
    <div className="h-[calc(100vh-140px)] flex flex-col" data-testid="conversations-page">
      {/* Header */}
      <div className="flex-shrink-0 mb-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Conversaciones
            </h1>
            <p className="text-slate-500 text-sm">Historial de chats con pacientes vía WhatsApp</p>
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={fetchConversations}
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-5 gap-4 min-h-0">
        {/* Conversations List */}
        <Card className={`stat-card lg:col-span-2 flex flex-col min-h-0 ${selectedConversation ? 'hidden lg:flex' : 'flex'}`}>
          <CardHeader className="flex-shrink-0 pb-3 border-b">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                placeholder="Buscar por nombre o teléfono..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 input-base"
                data-testid="search-conversations"
              />
            </div>
          </CardHeader>
          <CardContent className="flex-1 p-0 overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
              </div>
            ) : filteredConversations.length === 0 ? (
              <div className="text-center py-12 text-slate-500 px-4">
                <MessageSquare className="w-12 h-12 mx-auto mb-3 text-slate-300" />
                <p className="font-medium">No hay conversaciones</p>
                <p className="text-sm mt-1">Las conversaciones de WhatsApp aparecerán aquí</p>
              </div>
            ) : (
              <ScrollArea className="h-full">
                <div className="divide-y divide-slate-100">
                  {filteredConversations.map((conv) => (
                    <button
                      key={conv.id}
                      onClick={() => handleSelectConversation(conv)}
                      className={`w-full p-4 text-left hover:bg-slate-50 transition-colors ${
                        selectedConversation?.id === conv.id ? 'bg-sky-50 border-l-2 border-sky-500' : ''
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
                          <div className="flex items-center justify-between gap-2">
                            <p className="font-medium text-slate-900 truncate">
                              {conv.patient_name || 'Sin nombre'}
                            </p>
                            <Badge className={conv.status === 'active' ? 'badge-success text-xs' : 'badge-neutral text-xs'}>
                              {conv.status === 'active' ? 'Activa' : 'Cerrada'}
                            </Badge>
                          </div>
                          <p className="text-sm text-slate-500 flex items-center gap-1 mt-0.5">
                            <Phone className="w-3 h-3 flex-shrink-0" />
                            <span className="truncate">{conv.patient_phone}</span>
                          </p>
                          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                            <Clock className="w-3 h-3 flex-shrink-0" />
                            {conv.last_message_at 
                              ? format(parseISO(conv.last_message_at), "d MMM, HH:mm", { locale: es })
                              : 'Sin mensajes'}
                          </p>
                        </div>
                        <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
                      </div>
                    </button>
                  ))}
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>

        {/* Messages Panel */}
        <Card className={`stat-card lg:col-span-3 flex flex-col min-h-0 ${!selectedConversation ? 'hidden lg:flex' : 'flex'}`}>
          {!selectedConversation ? (
            <div className="flex-1 flex items-center justify-center text-slate-500">
              <div className="text-center">
                <MessageSquare className="w-16 h-16 mx-auto mb-4 text-slate-300" />
                <p className="text-lg font-medium">Selecciona una conversación</p>
                <p className="text-sm">para ver el historial de mensajes</p>
              </div>
            </div>
          ) : (
            <>
              {/* Conversation Header */}
              <CardHeader className="flex-shrink-0 border-b border-slate-100 py-3">
                <div className="flex items-center gap-3">
                  <button 
                    onClick={() => setSelectedConversation(null)}
                    className="lg:hidden p-2 hover:bg-slate-100 rounded-lg -ml-2"
                  >
                    <ArrowLeft className="w-5 h-5" />
                  </button>
                  <div className="w-10 h-10 bg-sky-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-sky-600 font-semibold">
                      {selectedConversation.patient_name?.charAt(0)?.toUpperCase() || '?'}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-base truncate">
                      {selectedConversation.patient_name || 'Sin nombre'}
                    </CardTitle>
                    <p className="text-sm text-slate-500 flex items-center gap-1">
                      <Phone className="w-3 h-3" />
                      {selectedConversation.patient_phone}
                    </p>
                  </div>
                  <Badge className={selectedConversation.status === 'active' ? 'badge-success' : 'badge-neutral'}>
                    {selectedConversation.status === 'active' ? 'Activa' : 'Cerrada'}
                  </Badge>
                </div>
              </CardHeader>

              {/* Messages */}
              <CardContent className="flex-1 p-0 overflow-hidden">
                {loadingMessages ? (
                  <div className="flex items-center justify-center h-full">
                    <Loader2 className="w-8 h-8 animate-spin text-sky-500" />
                  </div>
                ) : (
                  <ScrollArea className="h-full">
                    <div className="p-4 space-y-4">
                      {selectedConversation.messages?.length === 0 ? (
                        <div className="text-center py-8 text-slate-500">
                          <MessageSquare className="w-10 h-10 mx-auto mb-2 text-slate-300" />
                          <p className="text-sm">No hay mensajes en esta conversación</p>
                        </div>
                      ) : (
                        selectedConversation.messages?.map((msg) => (
                          <div 
                            key={msg.id}
                            className={`flex ${msg.sender === 'patient' ? 'justify-start' : 'justify-end'}`}
                            data-testid={`message-${msg.id}`}
                          >
                            <div className={`flex items-end gap-2 max-w-[85%] ${msg.sender === 'patient' ? '' : 'flex-row-reverse'}`}>
                              <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
                                msg.sender === 'patient' ? 'bg-slate-200' : 'bg-sky-500'
                              }`}>
                                {msg.sender === 'patient' ? (
                                  <User className="w-3.5 h-3.5 text-slate-600" />
                                ) : (
                                  <Bot className="w-3.5 h-3.5 text-white" />
                                )}
                              </div>
                              <div>
                                <div className={`rounded-2xl px-4 py-2.5 ${
                                  msg.sender === 'patient' 
                                    ? 'bg-slate-100 text-slate-900 rounded-bl-sm' 
                                    : 'bg-sky-500 text-white rounded-br-sm'
                                }`}>
                                  <p className="text-sm whitespace-pre-wrap break-words">{msg.content}</p>
                                </div>
                                <div className={`flex items-center gap-2 mt-1 ${msg.sender === 'patient' ? '' : 'justify-end'}`}>
                                  <span className="text-xs text-slate-400">
                                    {format(parseISO(msg.timestamp), "HH:mm", { locale: es })}
                                  </span>
                                  {msg.intent && getIntentBadge(msg.intent)}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </ScrollArea>
                )}
              </CardContent>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
