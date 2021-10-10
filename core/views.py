from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate, logout
from django.contrib.auth import login as auth_login
import requests
import base64
from urllib.parse import urlencode
from .forms import SearchForm, AddMusicForm
from .models import AccessTokenScoped
import environ

#Environ Settings
env = environ.Env()
environ.Env.read_env()

playlist_id = env.str('PLAYLIST_ID')
client_id = env.str('CLIENT_ID')
client_secret = env.str('CLIENT_SECRET')
redirect_uri = env.str('REDIRECT_URI')

#View inicial que mostra as músicas da playlist e dá as opções do sistema
def index(request):

    if str(request.user) == 'AnonymousUser': #verifica se o usuário está logado no sistema
        return redirect('user_in')
    else:
        if request.method == 'GET' and 'code' in request.GET: # verifica se o método é GET e se a requisição possui o parâmetro code
            code = request.GET['code']
            access_token = authScope(code)
            b = AccessTokenScoped(access_token_scoped=access_token) # Gera o token
            b.save() #salva no DB
        else:
            access_token = auth()

        # OBTER PLAYLIST NO SPOTIFY
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        endpoint = f"https://api.spotify.com/v1/playlists/{playlist_id}"
        r = requests.get(endpoint, headers=headers)
        results_playlist = r.json()

        # Salva informações da playlist como  nome, capa, músicas e as imagens delas
        playlist_name = results_playlist["name"]
        images = results_playlist["images"]
        playlist_cover = images[0]
        playlist_cover = playlist_cover['url']
        tracks = results_playlist['tracks']
        items = tracks['items']

        link_playlist_1 = results_playlist['external_urls']
        link_playlist = link_playlist_1['spotify']

        # Cria variiável de contexto a ser enviada para o template
        context = {
            'developer': 'Lindoso',
            'playlist_name': playlist_name,
            'playlist_cover': playlist_cover,
            'link_playlist': link_playlist,
            'items': items,
            'logged': True
        }
        return render(request, 'index.html', context)

#View about me
def contact(request):
    if str(request.user) == 'AnonymousUser': #verifica se o usuário está logado no sistema
            context = {
            'developer' : 'Lindoso',
            'logged' : False
        }
    else:
        context = {
            'developer' : 'Lindoso',
            'logged' : True
        }
    return render(request, 'contact.html', context)

#View do form que pesquisa a música a ser adicionada à playlist
def search_item(request):
    if str(request.user) == 'AnonymousUser': #verifica se o usuário está logado no sistema
        return redirect('user_in')
    else:
        form = SearchForm(request.POST or None)

        context = {
            'form' : form,
            'logged': True
        }

        return render(request, 'add_item_playlist.html', context)

#View que lista as músicas da pesquisa e adiciona à playlist
def add_item_playlist(request):
    if str(request.user) == 'AnonymousUser': #verifica se o usuário está logado no sistema
        return redirect('user_in')
    else:
        form = SearchForm(request.POST or None)

        access_token = auth()

        if str(request.method) == 'POST' :
            if form.is_valid():
                track = form.cleaned_data['track']

            # PESQUISAR POR ARTISTA OU MUSICA COM QUERY
            headers = {
                # "Authorization": f"Bearer {get_access_token_scoped()}"
                "Authorization": f"Bearer {access_token}"
            }
            endpoint = "https://api.spotify.com/v1/search"
            data = urlencode({"q": track, "type": "track"})
            lookup_url = f"{endpoint}?{data}"
            r = requests.get(lookup_url, headers=headers)

            form = AddMusicForm(request.POST or None)

            context = {
                'result': r,
                'form': form,
                'logged': True
            }

        return render(request, 'add_item_playlist_2.html', context)

def add_success(request):
    if str(request.user) == 'AnonymousUser': #verifica se o usuário está logado no sistema
        return redirect('user_in')
    else:
        latest_token = get_access_token_scoped()

        # SE O METODO FOR POST (ADICIONAR NOVA MÚSICA À PLAYLIST)
        if str(request.method) == 'POST':
            # Autenticando na API do Spotify
            track_id = request.POST.get('track_id')
            print(f'Track ID: {track_id}')
            headers = {
                "Authorization": f"Bearer {latest_token}",
                "Content-Type": "application/json"
            }
            endpoint = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?uris=spotify:track:{track_id}"
            r = requests.post(endpoint, headers=headers)
            results_add_playlist = r.json()

            if r.status_code in range(200, 299):
                messages.success(request, 'Track cadastrada com sucesso')
                context = {
                    'r': results_add_playlist,
                    'logged': True
                }
                return render(request, 'add_success.html', context)
            else:
                messages.error(request, f'Algo de errado aconteceu. Você gerou o seu Token na página inicial? --- {r.text}')
                return render(request, 'add_success.html')

def del_success(request):
    if str(request.user) == 'AnonymousUser': #verifica se o usuário está logado no sistema
        return redirect('user_in')
    else:
        latest_token = get_access_token_scoped()

        # SE O METODO FOR DELETE (Deletar NOVA MÚSICA À PLAYLIST)
        if str(request.method) == 'POST':
            # Autenticando na API do Spotify
            track_id = request.POST.get('track_id')
            print(f'Track ID: {track_id}')

            headers = {
                "Authorization": f"Bearer {latest_token}",
                "Content-Type": "application/json",
                "Accept" : "application/json"
            }

            data = '{"tracks":[{"uri":' +  f'"spotify:track:{track_id}"' + '}]}'

            print(f'Lista das Tracks: {data}')

            endpoint = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
            r = requests.delete(endpoint, data=data, headers=headers)

            print(f'Endpoint: {endpoint}')
            print(f'Response: {r}')
            print(f'Response: {r.text}')
            results_del_playlist = r.json()

            if r.status_code in range(200, 299):
                messages.success(request, 'Track removida com sucesso')
                context = {
                    'r': results_del_playlist,
                    'logged': True
                }
                return render(request, 'del_success.html', context)
            else:
                messages.error(request, f'Algo de errado aconteceu. Você gerou o seu Token na página inicial? --- {r.text}')
                return render(request, 'del_success.html')

# Cadastra um usuário (sem permissão pro admin do django)
def add_user(request):
    if request.method == "POST":
        form_user = UserCreationForm(request.POST)
        if form_user.is_valid():
            form_user.save()
            return redirect('index')
    else:
        form_user = UserCreationForm()
    return render(request, 'add_user.html', {'form_user': form_user})

# Loga usuário
def user_in(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        print(user)
        if user is not None:
            auth_login(request, user)
            return redirect('index')
        else:
            form_login = AuthenticationForm()
    else:
        form_login = AuthenticationForm()
    return render(request, 'login.html', {'form_login': form_login})

def user_out(request):
    logout(request)
    return redirect('index')

def authScope(code):

    # Credenciais do APP
    global client_id, client_secret
    client_creds = f"{client_id}:{client_secret}"
    client_creds_b64 = base64.b64encode(client_creds.encode())

    # Consulta o token para uso posterior
    token_url = 'https://accounts.spotify.com/api/token'
    token_data = {
        "grant_type": "authorization_code",
        "code": f"{code}",
        "redirect_uri": f"{redirect_uri}"
    }
    token_headers = {
        "Authorization": f"Basic {client_creds_b64.decode()}"  # base64 encoded
    }

    # Requisição para o endpoint api/token
    r = requests.post(token_url, data=token_data, headers=token_headers)

    valid_request = r.status_code in range(200, 299)

    # Token de Acesso
    if valid_request:
        token_response_data = r.json()
        access_token = token_response_data['access_token']
        return access_token
    else:
        print(f'Erro: {r} --- {r.text}')

def auth():

    # Credenciais do APP
    global client_id, client_secret
    client_creds = f"{client_id}:{client_secret}"
    client_creds_b64 = base64.b64encode(client_creds.encode())


    # Consulta o token para uso posterior
    token_url = 'https://accounts.spotify.com/api/token'
    token_data = {
        "grant_type": "client_credentials"
    }
    token_headers = {
        "Authorization": f"Basic {client_creds_b64.decode()}"  # base64 encoded
    }

    # Requisição para o endpoint api/token
    r = requests.post(token_url, data=token_data, headers=token_headers)

    valid_request = r.status_code in range(200, 299)

    # Token de Acesso
    if valid_request:
        token_response_data = r.json()
        access_token = token_response_data['access_token']
        return access_token

def get_access_token_scoped():
    access_token_scoped = AccessTokenScoped.objects.last()
    return access_token_scoped