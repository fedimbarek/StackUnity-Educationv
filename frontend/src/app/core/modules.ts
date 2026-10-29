// Miroir de backend/modules.py : un module = une route Angular + un blueprint Flask (/api/<id>)
export const MODULES = [
  { id: 'personnes', title: 'Personnes', icon: '👤' },
  { id: 'formations', title: 'Formations & Domaines', icon: '🎓' },
  { id: 'matieres', title: 'Matières & Pédagogie', icon: '📚' },
  { id: 'clubs', title: 'Clubs & Événements', icon: '🎭' },
  { id: 'organismes', title: 'Organismes & Stages', icon: '🏢' },
  { id: 'espaces', title: 'Espaces', icon: '🏫' },
  { id: 'inscriptions', title: 'Inscriptions', icon: '📝' },
  { id: 'bourses', title: 'Bourses', icon: '💰' },
  { id: 'sante', title: 'Santé', icon: '🩺' },
  { id: 'vie', title: 'Vie étudiante', icon: '🏠' },
];
export const DATATYPES = ['string', 'integer', 'decimal', 'float', 'double', 'boolean', 'date', 'dateTime', 'time', 'gYear', 'anyURI'];
